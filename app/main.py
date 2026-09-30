from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


class User(BaseModel):
    id: int
    name: str
    description: str | None = None
    age: int


fake_user_database = []
global_id = 0
app = FastAPI()


@app.post("/create_user")
def create_user(
        name: str,
        age: int,
        description: str | None = None
) -> str:
    global global_id
    next_id = global_id
    global_id += 1

    new_user = User(id=next_id,
                    name=name,
                    description=description,
                    age=age)

    fake_user_database.append(new_user)
    return f"{new_user.name} created successfully \n {new_user}"


@app.get("/users/{user_id}")
def read_item(user_id: int):
    for user in fake_user_database:
        if user.id == user_id:
            return {"user_id \n": user}

    raise HTTPException(status_code=404, detail="User not found")

@app.get("/users")
def read_item():
    return fake_user_database

@app.delete("/users/delete/{user_id}")
def delete_user(user_id: int):
    for idx, user in enumerate(fake_user_database):
        if user.id == user_id:
            del fake_user_database[idx]
            return f"User {user.name} deleted successfully \n {user}"

    raise HTTPException(status_code=404, detail="User not found")


@app.put("/users/update/{user_id}")
def update_user(user_id: int, age: int, name: str, description: str):
    for user in fake_user_database:
        if user.id == user_id:
            user.name = name
            user.age = age
            user.description = description
            return f"{user.name} updated successfully \n {user}"

    raise HTTPException(status_code=404, detail="User not found")
