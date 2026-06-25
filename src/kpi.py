import pandas as pd
import numpy as np

# ==========================================
# 1. UNIT FUNCTIONS (Calculs des KPI)
# ==========================================

def calculate_gross_yield(avg_rent_per_m2: float, median_price_per_m2: float) -> float:
    """
    Calcule le rendement brut annuel en %.
    Formule: (Loyer m²/mois x 12) / Prix m² x 100
    """
    if median_price_per_m2 <= 0:
        return 0.0
    return (avg_rent_per_m2 * 12) / median_price_per_m2 * 100


def calculate_vacancy_rate(vacant_housing: int, total_housing: int) -> float:
    """
    Calcule le taux de vacance immobilière en %.
    Formule: Logements vacants / Logements totaux x 100
    """
    if total_housing <= 0:
        return 0.0
    return (vacant_housing / total_housing) * 100


def calculate_tax_effort_ratio(avg_rent_per_m2: float, avg_fiscal_income: float) -> float:
    """
    Calcule le ratio d'effort fiscal basé sur le loyer annuel moyen au m².
    Formule: (Loyer m²/mois x 12) / Revenu fiscal moyen
    """
    if avg_fiscal_income <= 0:
        return 0.0
    annual_rent_per_m2 = avg_rent_per_m2 * 12
    return annual_rent_per_m2 / avg_fiscal_income


# ==========================================
# 2. SPECIFIC KPI NORMALIZATION FUNCTION
# ==========================================

def normalize_kpi(sequence: pd.Series) -> pd.Series:
    """
    Applique une normalisation à l'échelle nationale (0-100) spécifique 
    aux colonnes de KPI de notre dataset.
    """
    min_val = sequence.min()
    max_val = sequence.max()
    if max_val == min_val:
        return sequence * 0  # Évite la division par zéro si toutes les valeurs sont identiques
    return ((sequence - min_val) / (max_val - min_val)) * 100


# ==========================================
# 3. MASTER FUNCTION (Calcul du Score)
# ==========================================

def calculate_attractiveness_score(
    yield_norm: pd.Series, 
    effort_norm: pd.Series, 
    income_norm: pd.Series, 
    vacancy_norm: pd.Series
) -> pd.Series:
    """
    Calcule le score final d'attractivité (0-100) basé sur les pondérations du projet.
    Attention: L'effort fiscal et la vacance doivent être inversés (plus ils sont bas, mieux c'est).
    Pondération: 35% rendement + 25% effort (inv) + 20% richesse + 20% vacance (inv)
    """
    # Inversion des critères négatifs (le meilleur/plus bas devient 100, le pire/plus haut devient 0)
    inverted_effort = 100 - effort_norm
    inverted_vacancy = 100 - vacancy_norm
    
    # Application des coefficients de pondération du sujet
    score = (0.35 * yield_norm) + \
            (0.25 * inverted_effort) + \
            (0.20 * income_norm) + \
            (0.20 * inverted_vacancy)
            
    return score