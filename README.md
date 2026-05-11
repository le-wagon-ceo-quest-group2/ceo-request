# Olist CEO Request — Group 2

A data science exercise project from the Le Wagon Decision Science module, looking at the Olist e-commerce dataset and exploring whether (and how) the platform should remove under-performing sellers.

> 🎤 **Live demo**: <https://ceo-request.onrender.com/research-findings>
>
> 🧑‍💻 **Team**: Hang · Mario · Soodabeh

The demo is auto-deployed from `master` via Render's free tier — every push updates the live URL within 1–2 min. First visit after 15 min of idle may take ~30 s to wake up.

---

## Original problem brief

>❓ How many underperforming sellers should Olist remove to improve its profit, given that it has:
> - some revenues per sellers per months
> - some revenues per orders
> - some reputation costs (estimated) per bad reviews
> - some operational costs of IT system that grows with number of order items, but not linearly (scale effects)

---

## Running locally

```bash
pip install -r requirements.txt
python presentation/main.py
# → open http://127.0.0.1:8050
```