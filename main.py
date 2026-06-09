import os
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, Session, SQLModel, create_engine, select
from typing import List

# 1. MODELLO DATI (Fa sia da tabella PostgreSQL su Supabase sia da schema di validazione)
class Pizza(SQLModel, table=True):
    __tablename__ = "pizze"  # Nome della tabella all'interno di Supabase

    id: int | None = Field(default=None, primary_key=True)
    nome: str = Field(index=True, nullable=False)
    ingredienti: str = Field(nullable=False)
    prezzo: float = Field(gt=0, nullable=False)


# 2. CONFIGURAZIONE MOTORE DATABASE
# Recupera la stringa di connessione dall'ambiente (fornita da Supabase/Hosting)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("ERRORE: La variabile d'ambiente DATABASE_URL non è impostata!")

engine = create_engine(DATABASE_URL)

def create_db_and_tables():
    # Crea la tabella 'pizze' su Supabase se non esiste ancora
    SQLModel.metadata.create_all(engine)


# 3. INIZIALIZZAZIONE FASTAPI & CONFIGURAZIONE CORS
app = FastAPI(title="Pizzeria REST API - Supabase Edition", version="1.0.0")

# Abilitazione fondamentale del CORS per permettere al tuo Frontend React di comunicare con FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In produzione sostituisci con l'URL reale del tuo frontend React
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gestore dell'evento di avvio dell'applicazione
@app.on_event("startup")
def on_startup():
    create_db_and_tables()


# --- ENDPOINTS REST (CRUD) ---

# 1. READ ALL (GET /pizze) - Recupera l'elenco completo da Supabase
@app.get("/pizze", response_model=List[Pizza], status_code=status.HTTP_200_OK)
def get_all_pizze():
    with Session(engine) as session:
        # SQLModel esegue le query tramite session.exec()
        pizze = session.exec(select(Pizza)).all()
        return pizze


# 2. READ ONE (GET /pizze/{id}) - Recupera una singola pizza tramite ID
@app.get("/pizze/{pizza_id}", response_model=Pizza)
def get_pizza(pizza_id: int):
    with Session(engine) as session:
        pizza = session.get(Pizza, pizza_id)
        if not pizza:
            raise HTTPException(status_code=404, detail="Pizza non trovata")
        return pizza


# 3. CREATE (POST /pizze) - Aggiunge una nuova pizza (l'ID viene autoincrementato da Supabase)
@app.post("/pizze", response_model=Pizza, status_code=status.HTTP_201_CREATED)
def create_pizza(pizza: Pizza):
    with Session(engine) as session:
        session.add(pizza)
        session.commit()
        session.refresh(pizza)  # Recupera dal database l'ID appena generato
        return pizza


# 4. UPDATE (PUT /pizze/{id}) - Modifica i dati di una pizza esistente
@app.put("/pizze/{pizza_id}", response_model=Pizza)
def update_pizza(pizza_id: int, pizza_in: Pizza):
    with Session(engine) as session:
        # Cerchiamo l'elemento esistente nel DB di Supabase
        db_pizza = session.get(Pizza, pizza_id)
        if not db_pizza:
            raise HTTPException(status_code=404, detail="Pizza non trovata")
        
        # Estraiamo i nuovi dati escludendo i campi non inviati
        pizza_data = pizza_in.model_dump(exclude_unset=True)
        
        # Aggiorniamo i campi dell'oggetto nel database uno ad uno
        for key, value in pizza_data.items():
            if key != "id":  # Protezione per impedire la modifica accidentale della chiave primaria
                setattr(db_pizza, key, value)
        
        session.add(db_pizza)
        session.commit()
        session.refresh(db_pizza)
        return db_pizza


# 5. DELETE (DELETE /pizze/{id}) - Rimuove definitivamente una pizza da Supabase
@app.delete("/pizze/{pizza_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pizza(pizza_id: int):
    with Session(engine) as session:
        db_pizza = session.get(Pizza, pizza_id)
        if not db_pizza:
            raise HTTPException(status_code=404, detail="Pizza non trovata")
        
        session.delete(db_pizza)
        session.commit()
        return  # Con lo stato 204 non restituiamo alcun corpo nella risposta