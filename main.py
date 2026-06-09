from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List

# Importazioni per SQLAlchemy
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# --- CONFIGURAZIONE DATABASE SQLITE ---
DATABASE_URL = "sqlite:///./pizze.db"

# connect_args={"check_same_thread": False} è necessario solo per SQLite in ambienti multithread
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- MODELLO DATABASE (SQLAlchemy) ---
# Definisce la tabella reale che verrà creata dentro il file pizze.db
class PizzaDB(Base):
    __tablename__ = "pizze"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    ingredienti = Column(String)
    prezzo = Column(Float)


# Crea fisicamente la tabella nel database se non esiste già
Base.metadata.create_all(bind=engine)


# --- DIPENDENZA PER LA SESSIONE DEL DB ---
# Questa funzione apre una connessione al DB per ogni richiesta e la chiude automaticamente alla fine
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- POPOLAMENTO INIZIALE () ---
# Inserisce delle pizze di partenza se il database è completamente vuoto
def popola_database_iniziale():
    db = SessionLocal()
    if db.query(PizzaDB).count() == 0:
        pizze_iniziali = [
            PizzaDB(nome="Margherita", ingredienti="Pomodoro, Mozzarella, Basilico", prezzo=5.50),
            PizzaDB(nome="Diavola", ingredienti="Pomodoro, Mozzarella, Salame Piccante", prezzo=7.00),
            PizzaDB(nome="Capricciosa", ingredienti="Pomodoro, Mozzarella, Funghi, Carciofi, Prosciutto", prezzo=8.00)
        ]
        db.add_all(pizze_iniziali)
        db.commit()
    db.close()

popola_database_iniziale()


# --- INIZIALIZZAZIONE FASTAPI E CORS ---
app = FastAPI(title="Pizzeria REST API con SQLite", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- SCHEMI DATI (Pydantic v2) ---
class PizzaBase(BaseModel):
    nome: str = Field(..., example="Margherita")
    ingredienti: str = Field(..., example="Pomodoro, Mozzarella, Basilico")
    prezzo: float = Field(..., gt=0, example=6.50)

class PizzaCreate(PizzaBase):
    pass

class Pizza(PizzaBase):
    id: int

    # Dice a Pydantic di leggere i dati anche se sono oggetti ORM di SQLAlchemy
    class Config:
        from_attributes = True


# --- ENDPOINTS REST (CRUD) ---

# 1. READ ALL (GET /pizze) - Recupera tutte le pizze dal database
@app.get("/pizze", response_model=List[Pizza], status_code=status.HTTP_200_OK)
def get_all_pizze(db: Session = Depends(get_db)):
    return db.query(PizzaDB).all()


# 2. READ ONE (GET /pizze/{id}) - Recupera una singola pizza tramite ID
@app.get("/pizze/{pizza_id}", response_model=Pizza)
def get_pizza(pizza_id: int, db: Session = Depends(get_db)):
    pizza = db.query(PizzaDB).filter(PizzaDB.id == pizza_id).first()
    if pizza is None:
        raise HTTPException(status_code=404, detail="Pizza non trovata")
    return pizza


# 3. CREATE (POST /pizze) - Inserisce una nuova pizza nel database
@app.post("/pizze", response_model=Pizza, status_code=status.HTTP_201_CREATED)
def create_pizza(pizza_in: PizzaCreate, db: Session = Depends(get_db)):
    # Trasformiamo lo schema Pydantic nel modello del Database SQLAlchemy
    # L'ID viene autoincrementato automaticamente da SQLite
    new_pizza = PizzaDB(**pizza_in.model_dump())
    db.add(new_pizza)
    db.commit()      # Salva definitivamente nel file
    db.refresh(new_pizza)  # Recupera l'ID appena generato da SQLite
    return new_pizza


# 4. UPDATE (PUT /pizze/{id}) - Aggiorna i dati di una pizza esistente
@app.put("/pizze/{pizza_id}", response_model=Pizza)
def update_pizza(pizza_id: int, pizza_in: PizzaCreate, db: Session = Depends(get_db)):
    pizza_esistente = db.query(PizzaDB).filter(PizzaDB.id == pizza_id).first()
    if pizza_esistente is None:
        raise HTTPException(status_code=404, detail="Pizza non trovata")
    
    # Aggiorna i campi dell'oggetto ORM con i nuovi dati in arrivo dal frontend
    for key, value in pizza_in.model_dump().items():
        setattr(pizza_esistente, key, value)
        
    db.commit()
    db.refresh(pizza_esistente)
    return pizza_esistente


# 5. DELETE (DELETE /pizze/{id}) - Rimuove una pizza dal database
@app.delete("/pizze/{pizza_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pizza(pizza_id: int, db: Session = Depends(get_db)):
    pizza_esistente = db.query(PizzaDB).filter(PizzaDB.id == pizza_id).first()
    if pizza_esistente is None:
        raise HTTPException(status_code=404, detail="Pizza non trovata")
    
    db.delete(pizza_esistente)
    db.commit()
    return  # Restituisce una risposta vuota con codice 204