import os
from contextlib import asynccontextmanager
from typing import List, Generator
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, Session, SQLModel, create_engine, select

# --- 1. MODELLI DATI (Separazione delle responsabilità) ---
class PizzaBase(SQLModel):
    nome: str = Field(index=True, nullable=False)
    ingredienti: str = Field(nullable=False)
    prezzo: float = Field(gt=0, nullable=False)

class Pizza(PizzaBase, table=True):
    __tablename__ = "pizze"
    id: int | None = Field(default=None, primary_key=True)

class PizzaCreate(PizzaBase):
    pass  # Identico a PizzaBase, usato per validare l'input senza ID


# --- 2. CONFIGURAZIONE MOTORE DATABASE & LIFESPAN ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("ERRORE: La variabile d'ambiente DATABASE_URL non è impostata!")

engine = create_engine(DATABASE_URL)

# Gestore Lifespan moderno per rimpiazzare on_event
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Azioni all'avvio
    SQLModel.metadata.create_all(engine)
    yield
    # Azioni allo spegnimento (se necessarie)


# --- 3. INIZIALIZZAZIONE FASTAPI & CONFIGURAZIONE CORS ---
app = FastAPI(title="Pizzeria REST API - Supabase Edition", version="1.0.0")

# Configurazione CORS aperta a QUALSIASI frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <--- Questa riga permette l'accesso da qualsiasi URL/Dominio
    allow_credentials=False,  # <--- NOTA: Vedi spiegazione sotto se usi i cookie/autenticazione
    allow_methods=["*"],  # Permette tutti i metodi (GET, POST, PUT, DELETE, ecc.)
    allow_headers=["*"],  # Permette qualsiasi header (Content-Type, Authorization, ecc.)
)


# --- 4. DEPENDENCY INJECTION PER IL DATABASE ---
def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


# --- ENDPOINTS REST (CRUD) ---

# 1. READ ALL
@app.get("/pizze", response_model=List[Pizza], status_code=status.HTTP_200_OK)
def get_all_pizze(session: Session = Depends(get_session)):
    pizze = session.exec(select(Pizza)).all()
    return pizze


# 2. READ ONE
@app.get("/pizze/{pizza_id}", response_model=Pizza)
def get_pizza(pizza_id: int, session: Session = Depends(get_session)):
    pizza = session.get(Pizza, pizza_id)
    if not pizza:
        raise HTTPException(status_code=404, detail="Pizza non trovata")
    return pizza


# 3. CREATE (Usa PizzaCreate per l'input e restituisce Pizza con ID)
@app.post("/pizze", response_model=Pizza, status_code=status.HTTP_201_CREATED)
def create_pizza(pizza_in: PizzaCreate, session: Session = Depends(get_session)):
    db_pizza = Pizza.model_validate(pizza_in)
    session.add(db_pizza)
    session.commit()
    session.refresh(db_pizza)
    return db_pizza


# 4. UPDATE
@app.put("/pizze/{pizza_id}", response_model=Pizza)
def update_pizza(pizza_id: int, pizza_in: PizzaCreate, session: Session = Depends(get_session)):
    db_pizza = session.get(Pizza, pizza_id)
    if not db_pizza:
        raise HTTPException(status_code=404, detail="Pizza non trovata")
    
    pizza_data = pizza_in.model_dump(exclude_unset=True)
    for key, value in pizza_data.items():
        setattr(db_pizza, key, value)
    
    session.add(db_pizza)
    session.commit()
    session.refresh(db_pizza)
    return db_pizza


# 5. DELETE
@app.delete("/pizze/{pizza_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pizza(pizza_id: int, session: Session = Depends(get_session)):
    db_pizza = session.get(Pizza, pizza_id)
    if not db_pizza:
        raise HTTPException(status_code=404, detail="Pizza non trovata")
    
    session.delete(db_pizza)
    session.commit()
    return