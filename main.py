from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI(title="Pizzeria REST API", version="1.0.0")

# --- ABILITAZIONE CORS ---
# Permette all'applicazione React/HTML (anche se aperta come file locale o su localhost)
# di comunicare liberamente con questo backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In produzione inserisci l'URL specifico del tuo frontend
    allow_credentials=True,
    allow_methods=["*"],  # Permette GET, POST, PUT, DELETE, ecc.
    allow_headers=["*"],
)

# --- MODELLI DATI (Pydantic) ---
# Definisce la struttura dei dati che l'API si aspetta di ricevere e inviare
class PizzaBase(BaseModel):
    nome: str = Field(..., example="Margherita")
    ingredienti: str = Field(..., example="Pomodoro, Mozzarella, Basilico")
    prezzo: float = Field(..., gt=0, example=6.50)

class PizzaCreate(PizzaBase):
    pass

class Pizza(PizzaBase):
    id: int

# --- DATABASE IN MEMORIA (Mock) ---
# Usiamo una lista per simulare un database reale
db_pizze: List[Pizza] = [
    Pizza(id=1, nome="Margherita", ingredienti="Pomodoro, Mozzarella, Basilico", prezzo=5.50),
    Pizza(id=2, nome="Diavola", ingredienti="Pomodoro, Mozzarella, Salame Piccante", prezzo=7.00),
    Pizza(id=3, nome="Capricciosa", ingredienti="Pomodoro, Mozzarella, Funghi, Carciofi, Prosciutto", prezzo=8.00)
]
id_counter = 4

# --- ENDPOINTS REST (CRUD) ---

# 1. READ ALL (GET /pizze) - Mostra tutte le pizze
@app.get("/pizze", response_model=List[Pizza], status_code=status.HTTP_200_OK)
def get_all_pizze():
    return db_pizze

# 2. READ ONE (GET /pizze/{id}) - Mostra una singola pizza
@app.get("/pizze/{pizza_id}", response_model=Pizza)
def get_pizza(pizza_id: int):
    for pizza in db_pizze:
        if pizza.id == pizza_id:
            return pizza
    raise HTTPException(status_code=404, detail="Pizza non trovata")

# 3. CREATE (POST /pizze) - Aggiunge una nuova pizza
@app.post("/pizze", response_model=Pizza, status_code=status.HTTP_201_CREATED)
def create_pizza(pizza_in: PizzaCreate):
    global id_counter
    new_pizza = Pizza(
        id=id_counter,
        nome=pizza_in.nome,
        ingredienti=pizza_in.ingredienti,
        prezzo=pizza_in.prezzo
    )
    db_pizze.append(new_pizza)
    id_counter += 1
    return new_pizza

# 4. UPDATE (PUT /pizze/{id}) - Modifica una pizza esistente
@app.put("/pizze/{pizza_id}", response_model=Pizza)
def update_pizza(pizza_id: int, pizza_in: PizzaCreate):
    for index, pizza in enumerate(db_pizze):
        if pizza.id == pizza_id:
            updated_pizza = Pizza(id=pizza_id, **pizza_in.model_dump())
            db_pizze[index] = updated_pizza
            return updated_pizza
    raise HTTPException(status_code=404, detail="Pizza non trovata")

# 5. DELETE (DELETE /pizze/{id}) - Elimina una pizza
@app.delete("/pizze/{pizza_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pizza(pizza_id: int):
    for index, pizza in enumerate(db_pizze):
        if pizza.id == pizza_id:
            db_pizze.pop(index)
            return  # Con il codice 204 non si restituisce alcun corpo
    raise HTTPException(status_code=404, detail="Pizza non trovata")