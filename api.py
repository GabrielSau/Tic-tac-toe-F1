from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid

from src.logic import generate_grid, get_valid_drivers_for_cell
from src.database import SessionLocal, Driver

app = FastAPI()

# Stockage en mémoire des parties (suffit pour 2 joueurs)
games = {}

class JoinRequest(BaseModel):
    game_id: Optional[str] = None

class PlayRequest(BaseModel):
    game_id: str
    player: str  # "O" ou "X"
    row: int
    col: int
    driver_id: str

@app.post("/game/create")
def create_game():
    game_id = str(uuid.uuid4())[:8]
    grid = generate_grid()
    games[game_id] = {
        "grid": grid,
        "filled_cells": {},      # "r_c": "O" ou "X"
        "current_player": "O",
        "scores": {"O": 0, "X": 0},
        "players": [],           # ["O", "X"] quand les 2 sont connectés
        "winner": None,
        "is_draw": False,
        "status": "waiting"      # waiting | playing | finished
    }
    return {"game_id": game_id, "player": "O"}

@app.post("/game/join")
def join_game(req: JoinRequest):
    g = games.get(req.game_id)
    if not g:
        raise HTTPException(404, "Partie introuvable")
    if len(g["players"]) >= 2:
        raise HTTPException(400, "Partie pleine")
    if "O" not in g["players"]:
        g["players"].append("O")
        return {"player": "O"}
    g["players"].append("X")
    g["status"] = "playing"
    return {"player": "X"}

@app.get("/game/{game_id}/state")
def get_state(game_id: str):
    g = games.get(game_id)
    if not g:
        raise HTTPException(404)
    return g

@app.post("/game/play")
def play(req: PlayRequest):
    g = games.get(req.game_id)
    if not g:
        raise HTTPException(404)
    if g["status"] != "playing":
        raise HTTPException(400, "Partie non active")
    if g["current_player"] != req.player:
        raise HTTPException(400, "Pas ton tour")

    key = f"{req.row}_{req.col}"
    if key in g["filled_cells"]:
        raise HTTPException(400, "Case déjà jouée")

    row_crit = g["grid"]["rows"][req.row]
    col_crit = g["grid"]["cols"][req.col]
    valid_ids = get_valid_drivers_for_cell(row_crit, col_crit)

    next_player = "X" if req.player == "O" else "O"

    if req.driver_id in valid_ids:
        g["filled_cells"][key] = req.player
        winner = _check_winner(g["filled_cells"], req.player)
        if winner:
            g["winner"] = winner
            g["scores"][winner] += 1
            g["status"] = "finished"
        elif len(g["filled_cells"]) == 9:
            g["is_draw"] = True
            g["status"] = "finished"
        else:
            g["current_player"] = next_player
        return {"valid": True, "winner": g.get("winner"), "is_draw": g["is_draw"]}
    else:
        g["current_player"] = next_player
        return {"valid": False}

@app.post("/game/{game_id}/new_round")
def new_round(game_id: str):
    g = games.get(game_id)
    if not g:
        raise HTTPException(404)
    g["grid"] = generate_grid()
    g["filled_cells"] = {}
    g["current_player"] = "O"
    g["winner"] = None
    g["is_draw"] = False
    g["status"] = "playing"
    return {"ok": True}

def _check_winner(filled, player):
    fc = filled
    for r in range(3):
        if all(fc.get(f"{r}_{c}") == player for c in range(3)):
            return player
    for c in range(3):
        if all(fc.get(f"{r}_{c}") == player for r in range(3)):
            return player
    if all(fc.get(f"{i}_{i}") == player for i in range(3)):
        return player
    if all(fc.get(f"{i}_{2-i}") == player for i in range(3)):
        return player
    return None