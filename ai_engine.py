import datetime


def calculate_risk(symptoms, mood, nutrition):
    score = 100

    symptoms_lower = [s.lower() for s in symptoms]

    # Symptom-based deductions
    if "headache" in symptoms_lower:
        score -= 10
    if "swelling" in symptoms_lower:
        score -= 20
    if "dizziness" in symptoms_lower:
        score -= 15
    if "reduced fetal movement" in symptoms_lower:
        score -= 30
    if "bleeding" in symptoms_lower:
        score -= 40

    # Mood deductions
    if mood.lower() == "stressed":
        score -= 10
    elif mood.lower() == "very sad":
        score -= 20

    # Nutrition deductions
    if nutrition.lower() == "poor":
        score -= 15

    # Clamp score
    score = max(0, min(100, score))

    # Risk level logic
    if score >= 75:
        risk_level = "Low"
        escalation = False
        recommendation = "Continue regular monitoring and maintain a healthy diet."
    elif score >= 50:
        risk_level = "Medium"
        escalation = False
        recommendation = "Monitor symptoms closely and contact ASHA worker if symptoms worsen."
    else:
        risk_level = "High"
        escalation = True
        recommendation = "Immediate ASHA visit or PHC consultation required."

    return {
        "risk_score": score,
        "risk_level": risk_level,
        "escalation": escalation,
        "recommendation": recommendation,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }