# Rivers and Stones – Game Engine & Student Agent

This project implements the board game **Rivers and Stones**, along with a framework to run AI agents against each other or play manually.  

---

## Game Overview

Rivers and Stones is played on a **12 × 13 board**.  
Each player has **12 pieces**, each having **two sides**:

| Side | Purpose |
|------|---------|
| **Stone**| Used for scoring. Placing **4 Stones** in your Score Area wins the game. |
| **River**| Allows flowing movement across the board in its orientation (Horizontal / Vertical). |

### Objective
You **win** if:
- You place **4 Stone-side pieces** in your **Score Area**, **or**
- Your opponent **runs out of time**.

---

## Gameplay Rules

On each turn, a player may perform **exactly one** of the following actions:

| Action | Description |
|--------|-------------|
| **Move** | Move a piece 1 step (up/down/left/right). |
| **Push** | Move into a piece to push it (Stone pushes 1 step, River can push multiple). |
| **Flip & Rotate** | Flip Stone ↔ River; if River, choose orientation (H/V). |
| **Rotate River** | Rotate a River piece **90°** (horizontal ↔ vertical). |

### River Movement
Stepping onto a River allows sliding **along its flow direction** until blocked.  
Multiple connected rivers can chain into a long move.

### Pushing
- **Stone Push**: Pushes **one** adjacent piece **one step** if space is free.
- **River Push**: Pushes a Stone **multiple spaces** along its flow;  
  the pushing River **flips into a Stone** afterward.

---

## Project Structure
```bash
project/
│
├── gameEngine.py # It is an instance of the game. It can be run locally on your environment. You can run in GUI or CLI mode.
├── agent.py # It consists of the implementations of the Random Agent. 
├── student_agent.py # You need to implement your agent here. Some predefined function has been given.
└── requriments.txt
```

---

## 🛠 Installation

### Requirements
- Python **3.8+**

### Install dependencies
```bash
pip install -r requirements.txt
```

---
## Running The Game

### Human vs Human
```sh
python gameEngine.py --mode hvh
```
### Human vs AI

```sh
python gameEngine.py --mode hvai --circle random
```
### AI vs AI

```sh
python gameEngine.py --mode aivai --circle random --square student
```

### No GUI
```sh
python gameEngine.py --mode aivai --circle random --square student --nogui
```
