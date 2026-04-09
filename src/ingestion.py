import os
import fastf1
from database import SessionLocal, Driver, Team, Win, init_db
import matplotlib.pyplot as plt
import numpy as np
import fastf1
import os
from unidecode import unidecode

fastf1.Cache.enable_cache('data\\cache') 

CHAMPIONS_DATA = {
    2025: "Lando Norris",
    2024: "Max Verstappen", 2023: "Max Verstappen", 2022: "Max Verstappen", 2021: "Max Verstappen",
    2020: "Lewis Hamilton", 2019: "Lewis Hamilton", 2018: "Lewis Hamilton", 2017: "Lewis Hamilton",
    2016: "Nico Rosberg", 2015: "Lewis Hamilton", 2014: "Lewis Hamilton", 2013: "Sebastian Vettel",
    2012: "Sebastian Vettel", 2011: "Sebastian Vettel", 2010: "Sebastian Vettel", 2009: "Jenson Button",
    2008: "Lewis Hamilton", 2007: "Kimi Räikkönen", 2006: "Fernando Alonso", 2005: "Fernando Alonso",
    2004: "Michael Schumacher", 2003: "Michael Schumacher", 2002: "Michael Schumacher", 2001: "Michael Schumacher",
    2000: "Michael Schumacher", 1999: "Mika Häkkinen", 1998: "Mika Häkkinen", 1997: "Jacques Villeneuve",
    1996: "Damon Hill", 1995: "Michael Schumacher", 1994: "Michael Schumacher", 1993: "Alain Prost",
    1992: "Nigel Mansell", 1991: "Ayrton Senna", 1990: "Ayrton Senna", 1989: "Alain Prost",
    1988: "Ayrton Senna", 1987: "Nelson Piquet", 1986: "Alain Prost", 1985: "Alain Prost",
    1984: "Niki Lauda", 1983: "Nelson Piquet", 1982: "Keke Rosberg", 1981: "Nelson Piquet",
    1980: "Alan Jones", 1979: "Jody Scheckter", 1978: "Mario Andretti", 1977: "Niki Lauda",
    1976: "James Hunt", 1975: "Niki Lauda", 1974: "Emerson Fittipaldi", 1973: "Jackie Stewart",
    1972: "Emerson Fittipaldi", 1971: "Jackie Stewart", 1970: "Jochen Rindt", 1969: "Jackie Stewart",
    1968: "Graham Hill", 1967: "Denny Hulme", 1966: "Jack Brabham", 1965: "Jim Clark",
    1964: "John Surtees", 1963: "Jim Clark", 1962: "Graham Hill", 1961: "Phil Hill",
    1960: "Jack Brabham", 1959: "Jack Brabham", 1958: "Mike Hawthorn", 1957: "Juan Fangio",
    1956: "Juan Fangio", 1955: "Juan Fangio", 1954: "Juan Fangio", 1953: "Alberto Ascari",
    1952: "Alberto Ascari", 1951: "Juan Fangio", 1950: "Giuseppe Farina"
}

def save_circuit_map(year: int, gp_name: str, output_folder: str = "img/circuits") -> str | None:
    """Generate (or return existing) track map image for a given GP session.

    The function returns the path to the generated image or ``None`` on failure.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    track_name = {
        'cpa' : 'spa-francorchamps',
        'monte carlo' : 'monaco',
        'miami gardens' : 'miami',
        'yas island' : 'yas_marina'
    }

    gp_name = track_name.get(gp_name.lower(), gp_name)

        
    file_path = f"{output_folder}/{unidecode(gp_name.lower().replace(' ', '_'))}.png"
    
    if os.path.exists(file_path):
        return file_path

    try:
        session = fastf1.get_session(year, gp_name, 'Q')
        session.load(laps=True, telemetry=True, weather=False, messages=False)

        # verify that we actually have laps and telemetry
        if session.laps.empty:
            raise RuntimeError("pas de données de tour pour cette séance")
        lap = session.laps.pick_fastest()
        if lap is None:
            raise RuntimeError("aucun tour le plus rapide disponible")
        # pick_fastest returns a Lap object; ensure position data loaded
        try:
            pos = lap.get_pos_data()
        except Exception as ex:
            raise RuntimeError("position data non chargée") from ex
        circuit_info = session.get_circuit_info()

        track = pos.loc[:, ('X', 'Y')].to_numpy()
        track_angle = circuit_info.rotation / 180 * np.pi
        
        def rotate(xy, angle):
            rot_mat = np.array([[np.cos(angle), np.sin(angle)],
                                [-np.sin(angle), np.cos(angle)]])
            return np.matmul(xy, rot_mat)

        rotated_track = rotate(track, angle=track_angle)

        fig, ax = plt.subplots(figsize=(5, 5))
        ax.plot(rotated_track[:, 0], rotated_track[:, 1], color='black', lw=3)
        
        ax.axis('off')
        ax.axis('equal')
        
        plt.savefig(file_path, transparent=True, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        return file_path
        
    except Exception as e:
        print(f"Impossible de générer le tracé pour {gp_name}: {e}")
        return None

def apply_champions():
    session = SessionLocal()
    print("Mise à jour des titres de champions...")
    unique_champion_names = set(CHAMPIONS_DATA.values())
    
    for name in unique_champion_names:
        driver = session.query(Driver).filter(Driver.name.ilike(f"%{name}%")).first()
        if driver:
            driver.is_world_champion = True
    
    session.commit()
    session.close()
    print("Titres mis à jour !")

def ingest_f1_data(start_year, end_year):
    session = SessionLocal()
    
    for year in range(start_year, end_year + 1):
        print(f"--- Traitement de la saison {year} ---")
        
        try:
            schedule = fastf1.get_event_schedule(year)
            gp_list = schedule[schedule['EventFormat'] != 'testing']

            for _, event in gp_list.iterrows():
                # gp_name = event['EventName']
                circuit_name = event['Location'] # Ou event['CircuitName'] pour le nom complet
                print(f"Extraction : {circuit_name}...")
                
                race = fastf1.get_session(year, circuit_name, 'R')
                race.load(laps=False, telemetry=False, weather=False, messages=False)
                
                # Get circuit name
                # circuit_info = race.get_circuit_info()
                # circuit_name = circuit_info.name
                
                results = race.results

                for _, row in results.iterrows():
                    driver_id = row['DriverId'].lower()
                    driver_name = row['FullName']
                    team_id = row['TeamName'].replace(" ", "_").lower()
                    team_name = row['TeamName']
                    position = row['Position']
                    track_url = save_circuit_map(year, circuit_name)

                    # 1. Les écuries
                    team = session.query(Team).filter(Team.id == team_id).first()
                    if not team:
                        team = Team(
                            id=team_id, 
                            name=team_name
                        )
                        session.add(team)

                    # 2. les pilotes
                    driver = session.query(Driver).filter(Driver.id == driver_id).first()
                    if not driver:
                        driver = Driver(
                            id=driver_id, 
                            name=driver_name,
                            first_year=year,
                            last_year=year,
                            has_won_race=False
                        )
                        session.add(driver)
                    else:
                        # Mise à jour des années d'activité
                        driver.last_year = max(driver.last_year, year)
                        driver.first_year = min(driver.first_year, year)

                    # 3. lien Pilote <-> Écurie
                    if team not in driver.teams:
                        driver.teams.append(team)

                    # 4. les victoires
                    if position == 1:
                        driver.has_won_race = True
                        win_exists = session.query(Win).filter_by(
                            driver_id=driver_id, 
                            circuit_name=circuit_name, 
                            track_url=track_url,
                            year=year
                        ).first()
                        
                        if not win_exists:
                            new_win = Win(driver_id=driver_id, circuit_name=circuit_name, year=year, track_url=track_url)
                            session.add(new_win)

            session.commit()
            print(f"Saison {year} terminée et enregistrée.")

        except Exception as e:
            print(f"Erreur sur la saison {year}: {e}")
            session.rollback()

    session.close()

if __name__ == "__main__":
    init_db()

    print("Début de l'ingestion...")
    ingest_f1_data(2018, 2025)
    apply_champions()
    print("Ingestion terminée !")