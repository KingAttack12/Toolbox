import asyncio
import io
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from fastapi import FastAPI, APIRouter, HTTPException
from pypdf import PdfWriter, PdfReader
from PIL import Image
from app import accounts, auth, config, workload as module
from app.routers import monitor_routes, tools_pdf, tools_image, tools_media, tools_office, tools_youtube


class WorkloadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.queue = module.Workload()
        self.patches = [patch.object(accounts,'DB_PATH',Path(self.temp.name)/'accounts.sqlite3'),patch.object(config,'USERNAME','owner'),patch.object(config,'DATA_DIR',Path(self.temp.name)/'jobs'),patch.object(module,'workload',self.queue),patch.object(monitor_routes,'workload',self.queue)]
        for p in self.patches:p.start()
        auth._sessions.clear()
        for name in ['alice','bob','carol','dave']:
            accounts.set_enabled(True);accounts.request_account(name,'unused');accounts.decide(name,'approve')
        self.tokens = {name:auth.create_session(name) for name in ['owner','alice','bob','carol','dave']}
        self.app=FastAPI();self.app.include_router(monitor_routes.router)
        for router in [tools_pdf.router,tools_image.router,tools_media.router,tools_office.router,tools_youtube.router]:self.app.include_router(router)
        self.block=threading.Event();self.started=threading.Event();self.order=[]
        router=APIRouter(route_class=module.HeavyRoute)
        @router.post('/slow/{name}')
        def slow(name:str):
            self.started.set();self.block.wait(5);self.order.append(name)
            if name=='error':raise HTTPException(422,'Invalid test file')
            return {'ok':True}
        self.app.include_router(router)
        @self.app.get('/health')
        def health():return {'ok':True}
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='https://testserver')

    async def asyncTearDown(self):
        self.block.set();await self.client.aclose()
        for p in reversed(self.patches):p.stop()
        auth._sessions.clear();self.temp.cleanup()

    def headers(self,name='owner'):
        return {'Cookie':config.SESSION_COOKIE+'='+self.tokens[name]}

    async def until(self,fn):
        for _ in range(100):
            if fn():return
            await asyncio.sleep(.01)
        self.fail('State did not arrive')

    async def test_queue_fifo_capacity_duplicate_and_responsive_health(self):
        first=asyncio.create_task(self.client.post('/slow/first',headers=self.headers('alice')))
        await self.until(self.started.is_set)
        pending=[]
        for i,name in enumerate(['bob','carol','owner']):
            pending.append(asyncio.create_task(self.client.post('/slow/'+name,headers=self.headers(name))))
            await self.until(lambda:len(self.queue.snapshot()['waiting'])==i+1)
        self.assertEqual((await self.client.post('/slow/overflow',headers=self.headers('dave'))).status_code,429)
        self.assertEqual((await self.client.post('/slow/duplicate',headers=self.headers('alice'))).status_code,429)
        self.assertEqual((await asyncio.wait_for(self.client.get('/health'),.5)).status_code,200)
        own=await self.client.get('/api/tools/workload',headers=self.headers('bob'))
        self.assertEqual(own.json(),{'state':'waiting','position':1})
        self.assertNotIn('alice',own.text)
        self.block.set()
        for response in await asyncio.gather(first,*pending):self.assertEqual(response.status_code,200)
        self.assertEqual(self.order,['first','bob','carol','owner'])
        self.assertEqual(self.queue.snapshot()['completed'],4)

    async def test_cancel_waiter_timeout_and_failure_release(self):
        first=asyncio.create_task(self.client.post('/slow/first',headers=self.headers('alice')))
        await self.until(self.started.is_set)
        second=asyncio.create_task(self.client.post('/slow/second',headers=self.headers('bob')))
        await self.until(lambda:len(self.queue.snapshot()['waiting'])==1)
        second.cancel()
        with self.assertRaises(asyncio.CancelledError):await second
        self.assertEqual(len(self.queue.snapshot()['waiting']),0)
        self.queue.wait_seconds=.01
        self.assertEqual((await self.client.post('/slow/timeout',headers=self.headers('bob'))).status_code,429)
        self.block.set();await first
        self.assertEqual((await self.client.post('/slow/error',headers=self.headers('bob'))).status_code,422)
        self.assertIsNone(self.queue.snapshot()['running'])
        self.assertEqual((await self.client.post('/slow/next',headers=self.headers('bob'))).status_code,200)

    async def test_quota_authentication_and_dashboard_privacy(self):
        self.block.set()
        for _ in range(10):module.charge_quota('alice')
        self.assertEqual((await self.client.post('/slow/quota',headers=self.headers('alice'))).status_code,429)
        self.assertIsNone(self.queue.snapshot()['running'])
        self.assertEqual((await self.client.post('/slow/anonymous')).status_code,401)
        self.assertEqual((await self.client.get('/api/admin/load')).status_code,401)
        self.assertEqual((await self.client.get('/api/admin/load',headers=self.headers('bob'))).status_code,403)
        r=await self.client.get('/api/admin/load',headers=self.headers())
        self.assertEqual(r.status_code,200);self.assertEqual(r.headers['cache-control'],'no-store')
        self.assertIn('memory_vm',r.json());self.assertNotIn(self.tokens['owner'],r.text)
        for _ in range(30):module.charge_quota('owner')
        with self.assertRaises(HTTPException):module.charge_quota('owner')

    async def test_real_pdf_and_image_routes_and_error_cleanup(self):
        writer=PdfWriter();writer.add_blank_page(width=100,height=100);buf=io.BytesIO();writer.write(buf)
        r=await self.client.post('/api/tools/pdf/rotate',headers=self.headers(),files={'file':('test.pdf',buf.getvalue(),'application/pdf')},data={'angle':'90'})
        self.assertEqual(r.status_code,200);self.assertEqual(PdfReader(io.BytesIO(r.content)).pages[0].rotation,90)
        image=io.BytesIO();Image.new('RGB',(10,10),'red').save(image,format='PNG')
        r=await self.client.post('/api/tools/image/convert',headers=self.headers(),files={'file':('test.png',image.getvalue(),'image/png')},data={'format':'jpg'})
        self.assertEqual(r.status_code,200);self.assertEqual(Image.open(io.BytesIO(r.content)).format,'JPEG')
        r=await self.client.post('/api/tools/pdf/rotate',headers=self.headers(),files={'file':('bad.pdf',b'bad','application/pdf')})
        self.assertEqual(r.status_code,400);self.assertIsNone(self.queue.snapshot()['running'])
        for router in [tools_pdf.router,tools_image.router,tools_media.router,tools_office.router,tools_youtube.router]:
            self.assertTrue(all(isinstance(route,module.HeavyRoute) for route in router.routes))


    async def test_real_audio_office_and_ocr(self):
        import wave
        from docx import Document
        wav=io.BytesIO()
        with wave.open(wav,'wb') as audio:
            audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(8000);audio.writeframes(b'\0\0'*800)
        response=await self.client.post('/api/tools/media/mp4-to-mp3',headers=self.headers(),files={'file':('sample.wav',wav.getvalue(),'audio/wav')},data={'bitrate':'128'})
        self.assertEqual(response.status_code,200);self.assertEqual(response.headers['content-type'],'audio/mpeg');self.assertGreater(len(response.content),100)
        doc=Document();doc.add_paragraph('Toolbox synthetic conversion test');docx=io.BytesIO();doc.save(docx)
        response=await self.client.post('/api/tools/office/word-to-pdf',headers=self.headers(),files={'file':('sample.docx',docx.getvalue(),'application/octet-stream')})
        self.assertEqual(response.status_code,200);pdf=response.content;self.assertTrue(pdf.startswith(b'%PDF'))
        response=await self.client.post('/api/tools/office/pdf-to-word',headers=self.headers(),files={'file':('sample.pdf',pdf,'application/pdf')})
        self.assertEqual(response.status_code,200);self.assertTrue(response.content.startswith(b'PK'))
        response=await self.client.post('/api/tools/office/ocr',headers=self.headers(),files={'file':('sample.pdf',pdf,'application/pdf')},data={'language':'eng','dpi':'150'})
        self.assertEqual(response.status_code,200);self.assertIn('Toolbox',response.text)
        self.assertIsNone(self.queue.snapshot()['running'])
