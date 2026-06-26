import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv


load_dotenv()
DATA_DIR = "data/final"


engine = create_engine(
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}",
    connect_args={"options": "-csearch_path=operationnel"}
)

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT current_database(), current_schema()"))
        db, schema = result.fetchone()
        print(f"✓ Connecté à la base : {db}")
        print(f"✓ Schéma actif       : {schema}")

        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'operationnel'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        print(f"✓ Tables trouvées    : {tables}")

except Exception as e:
    print(f"✗ Erreur de connexion : {e}")

TABLES = [
"communes",
"demographics",
"transactions",
"loyers",
"foyers_fiscaux",
"parc_immobilier",
"indicateurs_macro",
"score_attractivite",
]

def load_table(table_name):
    filepath = os.path.join(DATA_DIR, f"{table_name}.csv")
    if not os.path.exists(filepath):
        print(f"⚠  Fichier manquant : {filepath}")
        return
    df = pd.read_csv(filepath)
    df.to_sql(
        name=table_name,
        con=engine,
        schema="operationnel",
        if_exists="append",
        index=False,
        method="multi",
        chunksize=5000
    )
    print(f"✓  {table_name:<25} {len(df):,} lignes insérées")

def verify():
    with engine.connect() as conn:
        print("\n── Vérification post-insertion ──")
        for table in TABLES:
            result = conn.execute(text(f"SELECT COUNT(*) FROM operationnel.{table}"))
            print(f"  {table:<25} {result.scalar():>10,} lignes")

if __name__ == "__main__":
    print("Début du chargement...\n")
    for table in TABLES:
        load_table(table)
    verify()
    print("\nChargement terminé.")