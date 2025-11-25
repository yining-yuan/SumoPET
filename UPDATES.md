# Project Updates: Input-Level Privacy Mode

## 1. Overview
We have introduced a new experimental mode called **`encrypted-input`**. This mode shifts the privacy protection mechanism from the *output* stage (Query-Level) to the *input* stage (Input-Level).

Instead of adding noise when a user asks a question (like "Where are the cars?"), we now add noise to the simulation data *before the simulation even starts*.

### Why is this interesting?
This represents a fundamental architectural choice in privacy-preserving systems:
*   **Query-Level (Adaptive/Static):** The system knows the truth but lies to the user to protect privacy. (Flexible, high utility for trusted users).
*   **Input-Level (Encrypted-Input):** The system *doesn't even know the truth*. It only holds noisy data. (High security, but rigid/lower utility).

---

## 2. System Architecture & Data Flow

Here is how data moves through the system in the new `encrypted-input` mode compared to the standard `baseline` mode.

### Standard Mode (Baseline / Adaptive)
1.  **Raw Data** (`persons.rou.xml`) $\rightarrow$ **SUMO Simulation** (Runs with perfect data).
2.  **User Query** $\rightarrow$ **Experiment Controller** reads perfect data from SUMO.
3.  **Privacy Engine** $\rightarrow$ Adds noise *on the fly* (e.g., adds 50m error).
4.  **Result** $\rightarrow$ User receives noisy data.

### New Encrypted-Input Mode
1.  **Raw Data** (`persons.rou.xml`) $\rightarrow$ **Encryption Script** (`build_encrypted_scenario.py`).
    *   *Action:* IDs are hashed, Departure times are shifted.
2.  **Encrypted Data** (`persons_encrypted.rou.xml`) $\rightarrow$ **SUMO Simulation**.
    *   *Note:* SUMO is now simulating a "phantom traffic" scenario. The cars are not where they are supposed to be.
3.  **User Query** $\rightarrow$ **Experiment Controller** reads data from SUMO.
    *   *Note:* The data is *already* noisy. The Controller doesn't need to add more noise.
4.  **Result** $\rightarrow$ User receives the noisy data directly.

---

## 3. Detailed Algorithm

We implemented two specific privacy mechanisms in the pre-processing stage:

### A. Pseudonymization (Identity Protection)
We replace the real Vehicle ID with a cryptographic hash. This prevents linking a vehicle's history across different days or sessions.
*   **Input:** `vehicle_id = "person_123"`
*   **Process:** `SHA-256("salt:person_123")`
*   **Output:** `anon_a1b2c3d4`

### B. Temporal Perturbation (Differential Privacy)
We add noise to the `depart` time (when a vehicle enters the simulation). This protects the exact time a user started their trip.
*   **Mechanism:** Laplace Mechanism
*   **Formula:** $t_{noisy} = t_{actual} + \text{Laplace}(\epsilon)$
*   **Effect:** A car that was supposed to leave at 8:00:00 might now leave at 8:00:15 or 7:59:45. This ripples through the simulation, causing the vehicle to be at a different location $x,y$ at any given time step $T$.

---

## 4. The "Ground Truth" Challenge

A major challenge we solved was **Evaluation**.

*   **The Problem:** If we ask SUMO "Where is car X?", it reports position $P_{noisy}$. If we compare this to what SUMO thinks is the truth ($P_{noisy}$), the error is 0. This gives a false sense of perfection (Accuracy = 100%).
*   **The Solution (Closed-Loop Evaluation):**
    1.  We first run the **Baseline** simulation and save the *actual* positions of all cars to a file (`baseline_ground_truth.pkl`).
    2.  When running the **Encrypted** simulation, we ignore what SUMO thinks is the truth.
    3.  Instead, we compare the **Encrypted Simulation Output** against the **Saved Baseline Ground Truth**.

$$ \text{Error} = | \text{Position}_{\text{Encrypted}} - \text{Position}_{\text{Baseline}} | $$

---

## 5. Summary of Code Changes

| File | Change Description |
| :--- | :--- |
| `build_encrypted_scenario.py` | **New File.** Script to parse XML routes, hash IDs, and perturb timestamps. |
| `run_experiment.py` | Updated to detect `encrypted-input` mode. It now triggers the build script and swaps the configuration file to use the encrypted routes. |
| `adaptive_pet_engine.py` | Updated `select_mechanism`. For `encrypted-input` mode, it returns `PrivacyMechanism.NONE` because the noise is already baked in. |
| `experiment_controller.py` | **Major Logic Update.** Added logic to save Ground Truth during baseline runs and load it during encrypted runs to ensure fair comparison. |

## 6. How to Run

To see the comparison properly, you must run the baseline first to establish the "Truth".

1.  **Generate Ground Truth:**
    ```bash
    python run_experiment.py --mode baseline
    ```
    *(Creates `outputs/baseline_ground_truth.pkl`)*

2.  **Run Encrypted Experiment:**
    ```bash
    python run_experiment.py --mode encrypted-input
    ```
    *(Loads the pkl file and calculates real error)*
