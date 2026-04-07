import sqlite3
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

driver_teams = Table('driver_teams', Base.metadata,
    Column('driver_id', String, ForeignKey('drivers.id')),
    Column('team_id', String, ForeignKey('teams.id'))
)

class Driver(Base):
    __tablename__ = 'drivers'
    id = Column(String, primary_key=True)
    name = Column(String)
    is_world_champion = Column(Boolean, default=False)
    has_won_race = Column(Boolean, default=False)
    first_year = Column(Integer)
    last_year = Column(Integer)
    
    # Relations
    teams = relationship('Team', secondary=driver_teams, back_populates='drivers')
    wins = relationship('Win', back_populates='driver')

class Team(Base):
    __tablename__ = 'teams'
    id = Column(String, primary_key=True)
    name = Column(String)
    # logo_url = Column(String)
    drivers = relationship('Driver', secondary=driver_teams, back_populates='teams')

class Win(Base):
    __tablename__ = 'wins'
    id = Column(Integer, primary_key=True)
    driver_id = Column(String, ForeignKey('drivers.id'))
    circuit_name = Column(String)
    track_url = Column(String)
    year = Column(Integer)
    driver = relationship('Driver', back_populates='wins')

# --- CONFIGURATION ET FONCTIONS ---

DATABASE_URL = "sqlite:///data/f1_grid.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Crée les tables dans le fichier .db"""
    Base.metadata.create_all(engine)
    print("Base de données initialisée avec succès.")

def check_driver_compatibility(driver_id: str, category_type: str, category_value) -> bool:
    """Return ``True`` if the driver matches the given category.

    ``category_type`` may be one of:
      * ``team`` - ``category_value`` is the team id or name
      * ``win`` - ``category_value`` is the circuit name
      * ``champion`` - ``category_value`` is ignored
      * ``decade`` - ``category_value`` is a tuple ``(start, end)``

    A database session is opened and closed for each call.
    """
    session = SessionLocal()
    driver = session.query(Driver).filter(Driver.id == driver_id).first()
    
    if not driver:
        return False

    try:
        if category_type == 'team':
            # category_value est le nom ou l'ID de l'écurie
            return any(t.id == category_value or t.name == category_value for t in driver.teams)
        
        elif category_type == 'win':
            # category_value est le nom du circuit (ex: 'Monaco')
            return any(w.circuit_name == category_value for w in driver.wins)
        
        elif category_type == 'champion':
            return driver.is_world_champion
        
        elif category_type == 'decade':
            # category_value est un tuple (2000, 2010)
            start, end = category_value
            # Vérifie si la période d'activité du pilote croise la décennie
            return not (driver.last_year < start or driver.first_year > end)

    finally:
        session.close()

if __name__ == "__main__":
    init_db()