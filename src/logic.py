
import random
from src.database import SessionLocal, Driver, Team, Win


CATEGORIES = [
    {"type": "team", "label": "A roulé pour {name}"},
    {"type": "win", "label": "A gagné à {name}"},
    {"type": "champion", "label": "Champion du Monde"},
    {"type": "decade", "label": "Actif dans les années {name}"},
    {"type": "one_race_winner", "label": "Vainqueur de GP"},
    {"type": "country", "label": "Nationalité : {name}"}
]

def get_valid_drivers_for_cell(crit_row, crit_col):
    """
    Retourne la liste des IDs de pilotes qui remplissent deux critères.
    """
    session = SessionLocal()
    query = session.query(Driver.id)

    # Application des filtres selon le type de catégorie
    for crit in [crit_row, crit_col]:
        if crit['type'] == 'team':
            query = query.join(Driver.teams).filter(Team.id == crit['value'])
        elif crit['type'] == 'country':
            query = query.filter(Driver.country == crit['value'])
        elif crit['type'] == 'win':
            query = query.join(Driver.wins).filter(Win.circuit_name == crit['value'])
        elif crit['type'] == 'champion':
            query = query.filter(Driver.is_world_champion == True)
        elif crit['type'] == 'decade':
            start, end = crit['value']
            query = query.filter(Driver.last_year >= start, Driver.first_year <= end)
        elif crit['type'] == 'one_race_winner':
            query = query.filter(Driver.has_won_race == True)

    results = [r[0] for r in query.all()]
    session.close()
    return results


def count_drivers_by_team(team_id: str) -> int:
    """Return the number of drivers who have driven for a given team."""
    session = SessionLocal()
    count = session.query(Driver).join(Driver.teams).filter(Team.id == team_id).count()
    session.close()
    return count

def generate_grid():
    """
    Génère une grille 3x3 et vérifie qu'elle a des solutions.
    """
    # Récupère des données utilisables pour les catégories
    session = SessionLocal()
    # on gardera aussi le nom pour le label
    all_teams = [(t.id, t.name) for t in session.query(Team.id, Team.name).all()]
    all_circuits = [w[0] for w in session.query(Win.circuit_name).distinct().all()]
    session.close()

    # construire un pool de critères distincts
    pool = []
    # équipes
    for tid, tname in all_teams:
        pool.append({'type': 'team', 'value': tid, 'label': CATEGORIES[0]['label'].format(name=tname)})
    # victoires sur circuits
    for circ in all_circuits:
        pool.append({'type': 'win', 'value': circ, 'label': CATEGORIES[1]['label'].format(name=circ)})
    # champion du monde (unique)
    pool.append({'type': 'champion', 'value': None, 'label': CATEGORIES[2]['label']})
    # décennies (on crée une entrée par décennie)
    for start in range(1950, 2021, 10):
        pool.append({'type': 'decade', 'value': (start, start+9), 'label': CATEGORIES[3]['label'].format(name=f'{start}s')})
    # vainqueurs d'une course
    pool.append({'type': 'one_race_winner', 'value': None, 'label': CATEGORIES[4]['label']})

    # Tentative de génération (on boucle jusqu'à ce que la pool donne une grille jouable)
    while True:
        # si pool est plus petit que 6, impossible
        if len(pool) < 6:
            raise RuntimeError("Pas assez de critères pour construire une grille")

        # on prélève six éléments distincts dans pool
        choix = random.sample(pool, 6)
        rows = choix[:3]
        cols = choix[3:]

        grid_possible = True
        solutions = {}

        for r in range(3):
            for c in range(3):
                valid_ids = get_valid_drivers_for_cell(rows[r], cols[c])
                if not valid_ids:
                    grid_possible = False
                    break
                solutions[f"{r}_{c}"] = valid_ids
            if not grid_possible:
                break

        if grid_possible:
            return {"rows": rows, "cols": cols, "solutions": solutions}