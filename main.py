import json
import os
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List

app = FastAPI(title="Pizzeria REST API con File Storage", version="2.0.0")

# --- ABILITAZIONE CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURAZIONE FILE JSON (DATABASE) ---
FILE_PATH = "pizze_db.json"

# Questa funzione crea il file JSON con dei dati iniziali se non esiste ancora
def inizializza_database():
    if not os.path.exists(FILE_PATH):
        pizze_iniziali = [
            {"id": 1, "nome": "Margherita", "ingredienti": "Pomodoro, Mozzarella, Basilico", "prezzo": 5.50},
            {"id": 2, "nome": "Diavola", "ingredienti": "Pomodoro, Mozzarella, Salame Piccante", "prezzo": 7.00},
            {"id": 3, "nome": "Capricciosa", "ingredienti": "Pomodoro, Mozzarella, Funghi, Carciofi, Prosciutto", "prezzo": 8.00}
        ]
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(pizze_iniziali, f, indent=4, ensure_ascii=False)

# Esegui l'inizializzazione all'avvio del file
inizializza_database()

# Funzioni di utilità per Leggere e Scrivere sul file JSON
def leggi_pizze_da_file() -> List[dict]:
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def scrivi_pizze_su_file(pizze_data: List[dict]):
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(pizze_data, f, indent=4, ensure_ascii=False)


# --- MODELLI DATI (Pydantic v2) ---
class PizzaBase(BaseModel):
    nome: str = Field(..., example="Margherita")
    ingredienti: str = Field(..., example="Pomodoro, Mozzarella, Basilico")
    prezzo: float = Field(..., gt=0, example=6.50)

class PizzaCreate(PizzaBase):
    pass

class Pizza(PizzaBase):
    id: int


# --- ENDPOINTS REST (CRUD) ---

# 1. READ ALL (GET /pizze)
@app.get("/pizze", response_model=List[Pizza], status_code=status.HTTP_200_OK)
def get_all_pizze():
    return leggi_pizze_da_file()


# 2. READ ONE (GET /pizze/{id})
@app.get("/pizze/{pizza_id}", response_model=Pizza)
def get_pizza(pizza_id: int):
    db_pizze = leggi_pizze_da_file()
    for pizza in db_pizze:
        if pizza["id"] == pizza_id:
            return pizza
    raise HTTPException(status_code=404, detail="Pizza non trovata")


# 3. CREATE (POST /pizze)
@app.post("/pizze", response_model=Pizza, status_code=status.HTTP_201_CREATED)
def create_pizza(pizza_in: PizzaCreate):
    db_pizze = leggi_pizze_da_file()
    
    # Calcola il nuovo ID in modo dinamico (prendi il massimo ID esistente e aggiungi 1)
    # Evita l'uso di variabili globali che falliscono in modalità multi-worker
    nuovo_id = max([p["id"] for p in db_pizze], default=0) + 1
    
    # Creiamo il dizionario della nuova pizza (usando il moderno .model_dump())
    nuova_pizza = {"id": nuovo_id, **pizza_in.model_dump()}
    
    db_pizze.append(nuova_pizza)
    scrivi_pizze_su_file(db_pizze)
    
    return nuova_pizza


# 4. UPDATE (PUT /pizze/{id})
@app.put("/pizze/{pizza_id}", response_model=Pizza)
def update_pizza(pizza_id: int, pizza_in: PizzaCreate):
    db_pizze = leggi_pizze_da_file()
    
    for index, pizza in enumerate(db_pizze):
        if pizza["id"] == pizza_id:
            # Creiamo l'oggetto aggiornato
            pizza_aggiornata = {"id": pizza_id, **pizza_in.model_dump()}
            # Sostituiamo nell'elenco
            db_pizze[index] = pizza_aggiornata
            
            scrivi_pizze_su_file(db_pizze)
            return pizza_aggiornata
            
    raise HTTPException(status_code=404, detail="Pizza non trovata")


# 5. DELETE (DELETE /pizze/{id})
@app.delete("/pizze/{pizza_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pizza(pizza_id: int):
    db_pizze = leggi_pizze_da_file()
    
    for index, pizza in enumerate(db_pizze):
        if pizza["id"] == pizza_id:
            db_pizze.pop(index)
            scrivi_pizze_su_file(db_pizze)
            return
            
    raise HTTPException(status_code=404, detail="Pizza non trovata")