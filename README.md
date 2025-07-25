# Chasedown

**Chasedown** is a fast-paced real-world tag-style game built around strategy, movement, and player interaction — both in person and online.

This project includes a web app and gameplay framework for running a competitive game where players (Runners and Hunters) complete challenges, tag opponents, and manage cooldowns and power-ups.

---

## 🎯 About the Game

Players are assigned roles as **Hunters** or **Runners**. Runners complete public challenges to earn points while evading Hunters. Hunters can't complete challenges and must tip a Runner, turning them back into a Runner and the runner into a Hunter A central dashboard tracks progress, timers, and tasks in real time.

---

## 📦 Features

- Live player dashboard  
- Role-based scoring and penalties
- Tasks to earn points  
- Admin-controlled global timers  
- GPS/Proof upload logic  
- Mobile-friendly interface  
- Flask + SQLAlchemy backend  

---

## 💡 Inspiration

This project is **inspired** by the competitive spirit and live-action structure of *Jet Lag: The Game* by Wendover Productions.  
> _This is a fan-inspired project and is **not affiliated with**, **endorsed by**, or **associated** with Jet Lag or Wendover._

All code, game rules, and original features are the intellectual property of **Remy Ellis**.

---

## ⚖️ License

This project is licensed under a **custom licence**.  
You may:
- Use, modify, and redistribute the code
- Build derivative versions
- Use it commercially (with attribution and royalties)

You **must**:
- Credit **Remy Ellis** in public versions
- Pay royalties on commercial use
- Not register trademarks or claim ownership of the IP

Full terms: see [`LICENSE`](./LICENSE)

---

## 🚀 Setup (optional)

If you’re running this locally:

```bash
pip install -r requirements.txt
python app.py
