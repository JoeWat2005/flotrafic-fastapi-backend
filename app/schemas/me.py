from pydantic import BaseModel


class UpdateMe(BaseModel):
    name: str


class ChangePassword(BaseModel):
    old_password: str
    new_password: str
