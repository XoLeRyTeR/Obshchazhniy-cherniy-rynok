from fastapi import Depends, Request

from src.api.dependencies.db import get_db


def service(service_class):
    def build(request: Request, db=Depends(get_db)):
        return service_class(db, request.app.state.settings)
    return build

