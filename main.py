# pylint: disable = import-error, missing-class-docstring, missing-module-docstring, too-few-public-methods, missing-function-docstring


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(debug=True)

origins = ["http://localhost:3000", "https://bbp.epfl.ch", "https://sonata.sbo.kcp.bbp.epfl.ch"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return "Hello worldf"
