import json

from aiohttp import web
from sqlalchemy.exc import IntegrityError

from models import Session, Announcement, engine, init_orm

app = web.Application()


async def init_db(app: web.Application):
    print("START")
    await init_orm()
    yield
    print("FINISH")
    await engine.dispose()


@web.middleware
async def session_middleware(request: web.Request, handler):
    async with Session() as session:
        request.session = session
        response = await handler(request)
        return response


app.cleanup_ctx.append(init_db)
app.middlewares.append(session_middleware)


def get_http_error(error_class, message):
    return error_class(
        text=json.dumps({"error": message}), content_type="application/json"
    )


async def get_ann_by_id(session: Session, ann_id: int):
    ann = await session.get(Announcement, ann_id)
    if ann is None:
        raise get_http_error(web.HTTPNotFound, "your announcement not found")
    return ann


async def add_ann(session: Session, ann: Announcement):
    try:
        session.add(ann)
        await session.commit()
    except IntegrityError:
        raise get_http_error(
            web.HTTPConflict, f"Announcement with id {ann.id} already exists"
        )
    return ann


class AnnView(web.View):
    @property
    def session(self) -> Session:
        return self.request.session

    @property
    def ann_id(self):
        return int(self.request.match_info["ann_id"])

    async def get_ann(self):
        return await get_ann_by_id(self.session, self.ann_id)

    async def get(self):
        ann = await self.get_ann()
        return web.json_response(ann.dict)

    async def post(self):
        json_data = await self.request.json()
        ann = Announcement(**json_data)
        await add_ann(self.session, ann)
        return web.json_response({"id": ann.id})

    async def patch(self):
        json_data = await self.request.json()
        ann = await self.get_ann()
        for field, value in json_data.items():
            setattr(ann, field, value)
        await add_ann(self.session, ann)
        return web.json_response(ann.dict)

    async def delete(self):
        ann = await self.get_ann()
        await self.session.delete(ann)
        await self.session.commit()
        return web.json_response({"status": "deleted"})


app.add_routes(
    [
        web.get("/ann/{ann_id:\d+}", AnnView),
        web.patch("/ann/{ann_id:\d+}", AnnView),
        web.delete("/ann/{ann_id:\d+}", AnnView),
        web.post("/ann", AnnView),
    ]
)

web.run_app(app, port=8080)
