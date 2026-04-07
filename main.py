from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import src.logic # Le fichier qu'on a imaginé précédemment
from src.database import SessionLocal, Driver, init_db

# optionnel : on peut ingérer les données automatiquement au démarrage
from src.ingestion import ingest_f1_data, apply_champions

app = FastAPI()

# Permet à ton futur frontend de communiquer avec ton backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    # créer les tables si elles n'existent pas encore
    init_db()

    # si la BDD est vide (pas d'écurie), on peut lancer l'ingestion initiale
    session = SessionLocal()
    if session.query(Driver).count() == 0:
        print("base vide détectée, lancement de l'ingestion (peut prendre plusieurs minutes)...")
        ingest_f1_data(2020, 2025)
        apply_champions()
        print("ingestion automatique terminée")
    session.close()


@app.get("/new-game")
def get_new_game():
    """Génère une nouvelle grille jouable"""
    grid = src.logic.generate_grid()
    if not grid:
        raise HTTPException(status_code=500, detail="Impossible de générer une grille valide")
    return grid

@app.get("/search-driver")
def search_driver(q: str):
    """Recherche un pilote pour l'autocomplétion"""
    session = SessionLocal()
    # On cherche les pilotes dont le nom contient la chaîne 'q'
    results = session.query(Driver).filter(Driver.name.ilike(f"%{q}%")).limit(10).all()
    session.close()
    return [{"id": d.id, "name": d.name} for d in results]

@app.post("/validate")
def validate_answer(driver_id: str, row: int, col: int, solutions: dict):
    """Vérifie si le choix du joueur est correct pour une case donnée"""
    cell_key = f"{row}_{col}"
    if cell_key in solutions and driver_id in solutions[cell_key]:
        return {"correct": True}
    return {"correct": False}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)