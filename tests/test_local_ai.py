import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from app import accounts, auth, config, workload
from app.routers import local_ai


class LocalAITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(accounts, 'DB_PATH', Path(self.temp.name)/'accounts.sqlite3'),
                        patch.object(config, 'USERNAME', 'owner'), patch.object(config, 'LOCAL_AI_ENABLED', True),
                        patch.object(auth, '_sessions', {}), patch.object(workload, 'workload', workload.Workload())]
        for item in self.patches: item.start()
        with accounts.database() as db:
            db.execute("INSERT INTO accounts(username,password_hash,status,created,expires) VALUES ('guest','unused','active',?,253402300799)", (time.time(),))
        app = FastAPI(); app.include_router(local_ai.router); app.include_router(local_ai.work_router)
        self.client = TestClient(app, base_url='https://testserver')
        self.owner = auth.create_session('owner'); self.guest = auth.create_session('guest')

    def tearDown(self):
        self.client.close()
        for item in reversed(self.patches): item.stop()
        self.temp.cleanup()

    def login(self, token): self.client.cookies.set(config.SESSION_COOKIE, token)
    def run_ai(self, **values):
        return self.client.post('/api/admin/ai/generate', headers={'X-Toolbox-Request':'1'}, json={'mode':'summary','text':'Un document de test suffisamment long.', **values})

    def test_owner_csrf_flag_and_input_limits(self):
        self.assertEqual(self.run_ai().status_code,401)
        self.login(self.guest)
        self.assertEqual(self.run_ai().status_code,403)
        self.assertEqual(self.client.get('/api/admin/ai/status').status_code,403)
        self.assertIsNone(workload.workload.snapshot()['running'])
        self.login(self.owner)
        self.assertEqual(self.run_ai(text='x'*2001).status_code,422)
        self.assertEqual(self.run_ai(mode='execute').status_code,422)
        self.assertEqual(self.client.post('/api/admin/ai/generate',json={'mode':'summary','text':'Un document de test suffisamment long.'}).status_code,403)
        with patch.object(config,'LOCAL_AI_ENABLED',False): self.assertEqual(self.run_ai().status_code,503)

    def test_streamed_answer_settings_no_store_and_release(self):
        self.login(self.owner)
        answer = {'message':{'content':'Un résumé.'},'done':True,'eval_count':10,'eval_duration':1000000000}
        with patch.object(local_ai,'urlopen', return_value=io.BytesIO((json.dumps(answer)+'\n').encode())) as request:
            response=self.run_ai()
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()['text'],'Un résumé.')
            self.assertEqual(response.headers['cache-control'],'no-store')
            payload=json.loads(request.call_args.args[0].data)
            self.assertFalse(payload['think']);self.assertTrue(payload['stream'])
            self.assertEqual(payload['options']['num_thread'],2)
            self.assertEqual(payload['options']['num_predict'],192)
        self.assertIsNone(workload.workload.snapshot()['running'])

    def test_engine_failure_timeout_and_shared_queue(self):
        self.login(self.owner)
        with patch.object(local_ai,'urlopen',side_effect=TimeoutError):self.assertEqual(self.run_ai().status_code,504)
        with patch.object(local_ai,'urlopen',return_value=io.BytesIO(b'invalid\n')):self.assertEqual(self.run_ai().status_code,503)
        self.assertIsNone(workload.workload.snapshot()['running'])
        entry=workload.workload.admit('owner','conversion');workload.workload.start(entry)
        self.assertEqual(self.run_ai().status_code,429)
        workload.workload.release(entry)
