"""
Main entry point - Tic-Tac-Toe F1 (Kivy)
"""
import sys
import os
from src.database import SessionLocal, Driver, init_db


def init_database():
    """Initialise la base de données (juste créer les tables)"""
    init_db()
    print("✓ Base de données initialisée")


def main():
    """Lance l'interface Kivy"""
    print("📱 Lancement de Tic-Tac-Toe F1 en Kivy")
    init_database()
    from src.ui_kivy import TicTacToeF1App
    app = TicTacToeF1App()
    app.run()


if __name__ == "__main__":
    main()