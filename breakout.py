"""
Breakout (Brick Breaker) Game
==============================
Built with Python's tkinter library using procedural programming.
Designed for Stanford's Code in Place final project.

Controls:
  - Move mouse left/right to control the paddle
  - OR use the Left/Right arrow keys
  - Press SPACE to launch the ball at the start
  - Press R to restart after Game Over
"""

import tkinter as tk
import math
import random

# ─────────────────────────────────────────────
#  GAME CONSTANTS  (edit these to customise!)
# ─────────────────────────────────────────────

WINDOW_WIDTH  = 600
WINDOW_HEIGHT = 700
BACKGROUND    = "#0d0d1a"       # Deep space-blue background

# Paddle settings
PADDLE_WIDTH  = 100
PADDLE_HEIGHT = 12
PADDLE_Y      = WINDOW_HEIGHT - 50
PADDLE_COLOR  = "#e0e0ff"
PADDLE_SPEED  = 18              # Pixels moved per arrow-key press

# Ball settings
BALL_RADIUS   = 10
BALL_COLOR    = "#ffffff"
BALL_SPEED    = 5               # Starting speed (pixels per frame tick)

# Brick grid settings
BRICK_ROWS    = 6
BRICK_COLS    = 10
BRICK_WIDTH   = 52
BRICK_HEIGHT  = 20
BRICK_PADDING = 4               # Gap between bricks
BRICK_TOP     = 60              # Y-position of the top brick row

# Row colours (one per row, bottom-to-top)
ROW_COLORS = ["#ff4f4f", "#ff7f3f", "#ffd700", "#7fff4f", "#3fbfff", "#bf7fff"]

# Animation speed (milliseconds between each frame)
FRAME_DELAY = 16                # ~60 fps


# ─────────────────────────────────────────────
#  GAME STATE  (one dictionary holds everything)
# ─────────────────────────────────────────────

# We use a single mutable dict so all functions can read/write shared state
# without needing global variables for every value.
state = {
    "ball_x":     WINDOW_WIDTH  / 2,
    "ball_y":     WINDOW_HEIGHT / 2,
    "ball_dx":    0,            # Horizontal velocity (set on launch)
    "ball_dy":    0,            # Vertical velocity   (set on launch)
    "launched":   False,        # Has the ball been launched yet?
    "paddle_x":   WINDOW_WIDTH  / 2 - PADDLE_WIDTH / 2,
    "bricks":     {},           # Maps canvas item ID → True (still alive)
    "score":      0,
    "lives":      3,
    "game_over":  False,
    "win":        False,
}


# ─────────────────────────────────────────────
#  SETUP FUNCTIONS
# ─────────────────────────────────────────────

def create_bricks(canvas):
    """
    Draw the full grid of bricks on the canvas and record their IDs
    in state["bricks"] so we can detect hits and remove them later.

    Each brick's canvas ID maps to True (alive). When hit, we delete
    the canvas item and remove the entry from the dictionary.
    """
    state["bricks"] = {}
    for row in range(BRICK_ROWS):
        color = ROW_COLORS[row % len(ROW_COLORS)]
        for col in range(BRICK_COLS):
            x1 = col * (BRICK_WIDTH + BRICK_PADDING) + BRICK_PADDING
            y1 = BRICK_TOP + row * (BRICK_HEIGHT + BRICK_PADDING)
            x2 = x1 + BRICK_WIDTH
            y2 = y1 + BRICK_HEIGHT
            brick_id = canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=color, outline="#ffffff", width=1
            )
            state["bricks"][brick_id] = True


def reset_ball(canvas, ball_obj):
    """
    Place the ball back in the centre of the screen and stop it.
    Called at the start of the game and after losing a life.
    """
    state["ball_x"]   = WINDOW_WIDTH  / 2
    state["ball_y"]   = WINDOW_HEIGHT / 2
    state["ball_dx"]  = 0
    state["ball_dy"]  = 0
    state["launched"] = False
    canvas.coords(
        ball_obj,
        state["ball_x"] - BALL_RADIUS,
        state["ball_y"] - BALL_RADIUS,
        state["ball_x"] + BALL_RADIUS,
        state["ball_y"] + BALL_RADIUS,
    )


def launch_ball():
    """
    Give the ball its initial velocity when the player presses SPACE.
    The horizontal direction is randomised slightly so each round
    feels different.
    """
    if state["launched"] or state["game_over"]:
        return
    angle = random.uniform(210, 330)          # degrees (pointing upward)
    rad   = math.radians(angle)
    state["ball_dx"] = BALL_SPEED * math.cos(rad)
    state["ball_dy"] = BALL_SPEED * math.sin(rad)
    state["launched"] = True


# ─────────────────────────────────────────────
#  COLLISION DETECTION
# ─────────────────────────────────────────────

def check_wall_collisions():
    """
    Bounce the ball off the three solid walls (left, right, top).
    If the ball exits through the bottom, a life is lost.

    Returns True if the ball fell out of bounds (lost a life).
    """
    bx, by = state["ball_x"], state["ball_y"]

    # Left wall
    if bx - BALL_RADIUS <= 0:
        state["ball_dx"] = abs(state["ball_dx"])   # Force rightward

    # Right wall
    if bx + BALL_RADIUS >= WINDOW_WIDTH:
        state["ball_dx"] = -abs(state["ball_dx"])  # Force leftward

    # Top wall
    if by - BALL_RADIUS <= 0:
        state["ball_dy"] = abs(state["ball_dy"])   # Force downward

    # Bottom – ball is lost
    if by - BALL_RADIUS > WINDOW_HEIGHT:
        return True

    return False


def check_paddle_collision():
    """
    Check whether the ball has hit the paddle.

    We use a simple Axis-Aligned Bounding Box (AABB) test:
    the ball's bounding box must overlap the paddle's bounding box.
    When a hit is detected the ball is sent back upward, and a small
    horizontal nudge is added based on WHERE on the paddle it hit –
    hitting the edge kicks the ball sideways, just like the arcade original.
    """
    px = state["paddle_x"]
    bx = state["ball_x"]
    by = state["ball_y"]

    paddle_left   = px
    paddle_right  = px + PADDLE_WIDTH
    paddle_top    = PADDLE_Y
    paddle_bottom = PADDLE_Y + PADDLE_HEIGHT

    # Only process if the ball is moving downward (avoid double-bounce)
    if state["ball_dy"] <= 0:
        return

    if (bx + BALL_RADIUS >= paddle_left and
            bx - BALL_RADIUS <= paddle_right and
            by + BALL_RADIUS >= paddle_top and
            by - BALL_RADIUS <= paddle_bottom):

        # Reflect vertically
        state["ball_dy"] = -abs(state["ball_dy"])

        # Add spin based on offset from paddle centre
        offset = (bx - (paddle_left + PADDLE_WIDTH / 2)) / (PADDLE_WIDTH / 2)
        state["ball_dx"] += offset * 2          # Nudge horizontally


def check_brick_collisions(canvas):
    """
    Check whether the ball has hit any brick.

    How it works:
      1. Build the ball's bounding box.
      2. Loop over every surviving brick.
      3. Ask tkinter for that brick's current coordinates.
      4. Test for AABB overlap.
      5. If a hit occurs: delete the brick, update the score, and
         decide whether to bounce horizontally or vertically by
         comparing how deeply the ball overlaps on each axis.

    Only the FIRST hit per frame is processed (break after first hit)
    to avoid the ball tunnelling through a thin row of bricks.
    """
    bx = state["ball_x"]
    by = state["ball_y"]
    ball_left   = bx - BALL_RADIUS
    ball_right  = bx + BALL_RADIUS
    ball_top    = by - BALL_RADIUS
    ball_bottom = by + BALL_RADIUS

    hit_id = None   # We'll process at most one brick per frame

    for brick_id in list(state["bricks"]):
        # Get this brick's pixel coordinates from the canvas
        x1, y1, x2, y2 = canvas.coords(brick_id)

        # AABB overlap test
        if (ball_right  >= x1 and
                ball_left   <= x2 and
                ball_bottom >= y1 and
                ball_top    <= y2):
            hit_id = brick_id

            # Determine overlap depth on each axis to pick the bounce axis
            overlap_x = min(ball_right - x1, x2 - ball_left)
            overlap_y = min(ball_bottom - y1, y2 - ball_top)

            if overlap_x < overlap_y:
                state["ball_dx"] *= -1    # Horizontal bounce
            else:
                state["ball_dy"] *= -1    # Vertical bounce (most common)

            break   # One brick at a time

    if hit_id is not None:
        canvas.delete(hit_id)
        del state["bricks"][hit_id]
        state["score"] += 10


# ─────────────────────────────────────────────
#  HUD  (score + lives display)
# ─────────────────────────────────────────────

def update_hud(canvas, score_text, lives_text):
    """Update the on-screen score and lives counter every frame."""
    canvas.itemconfig(score_text, text=f"Score: {state['score']}")
    canvas.itemconfig(lives_text, text=f"Lives: {state['lives']}")


# ─────────────────────────────────────────────
#  MAIN ANIMATION LOOP
# ─────────────────────────────────────────────

def game_loop(canvas, ball_obj, paddle_obj, score_text, lives_text,
              message_text, sub_text):
    """
    The heart of the game – called every FRAME_DELAY milliseconds
    by tkinter's `after` scheduler.

    Each tick:
      1. Skip physics if the ball hasn't been launched yet.
      2. Move the ball by (dx, dy).
      3. Run all collision checks.
      4. Update canvas positions for ball and paddle.
      5. Update the HUD.
      6. Check win/lose conditions.
      7. Schedule the next tick.
    """

    if not state["game_over"]:
        if state["launched"]:
            # ── Move ball ──────────────────────────────────────────
            state["ball_x"] += state["ball_dx"]
            state["ball_y"] += state["ball_dy"]

            # ── Collisions ─────────────────────────────────────────
            fell_out = check_wall_collisions()
            check_paddle_collision()
            check_brick_collisions(canvas)

            # ── Lost a life? ────────────────────────────────────────
            if fell_out:
                state["lives"] -= 1
                if state["lives"] <= 0:
                    state["game_over"] = True
                    canvas.itemconfig(message_text, text="GAME OVER",
                                      fill="#ff4444")
                    canvas.itemconfig(sub_text,
                                      text=f"Final score: {state['score']}   |   Press R to restart",
                                      fill="#aaaacc")
                else:
                    # Still have lives – reset ball but keep bricks
                    reset_ball(canvas, ball_obj)
                    canvas.itemconfig(sub_text,
                                      text=f"Lives left: {state['lives']}  –  press SPACE to launch",
                                      fill="#aaaacc")
                    canvas.itemconfig(message_text, text="")

            # ── All bricks cleared? ─────────────────────────────────
            if len(state["bricks"]) == 0 and not state["game_over"]:
                state["game_over"] = True
                state["win"] = True
                canvas.itemconfig(message_text, text="YOU WIN! 🎉",
                                  fill="#7fff4f")
                canvas.itemconfig(sub_text,
                                  text=f"Score: {state['score']}   |   Press R to restart",
                                  fill="#aaaacc")

        # ── Redraw ball ────────────────────────────────────────────
        canvas.coords(
            ball_obj,
            state["ball_x"] - BALL_RADIUS,
            state["ball_y"] - BALL_RADIUS,
            state["ball_x"] + BALL_RADIUS,
            state["ball_y"] + BALL_RADIUS,
        )

        # ── Redraw paddle ──────────────────────────────────────────
        px = state["paddle_x"]
        canvas.coords(paddle_obj,
                      px, PADDLE_Y,
                      px + PADDLE_WIDTH, PADDLE_Y + PADDLE_HEIGHT)

        # ── HUD ────────────────────────────────────────────────────
        update_hud(canvas, score_text, lives_text)

        # ── "Press SPACE" hint while waiting to launch ─────────────
        if not state["launched"]:
            canvas.itemconfig(sub_text,
                              text="Press SPACE to launch the ball",
                              fill="#7777aa")
        elif state["launched"] and canvas.itemcget(sub_text, "text").startswith("Press"):
            canvas.itemconfig(sub_text, text="")

    # Schedule the next frame (tkinter's way of doing animation)
    canvas.after(FRAME_DELAY, game_loop, canvas, ball_obj, paddle_obj,
                 score_text, lives_text, message_text, sub_text)


# ─────────────────────────────────────────────
#  INPUT HANDLERS
# ─────────────────────────────────────────────

def on_mouse_move(event):
    """Keep the paddle centred on the mouse's X position."""
    new_x = event.x - PADDLE_WIDTH / 2
    # Clamp so the paddle stays on screen
    state["paddle_x"] = max(0, min(new_x, WINDOW_WIDTH - PADDLE_WIDTH))


def on_key_press(event, canvas, ball_obj, paddle_obj, score_text,
                 lives_text, message_text, sub_text):
    """
    Handle keyboard input:
      Left / Right arrows → move paddle
      Space               → launch ball
      R                   → restart after game over
    """
    key = event.keysym

    if key == "Left":
        state["paddle_x"] = max(0, state["paddle_x"] - PADDLE_SPEED)

    elif key == "Right":
        state["paddle_x"] = min(WINDOW_WIDTH - PADDLE_WIDTH,
                                state["paddle_x"] + PADDLE_SPEED)

    elif key == "space":
        launch_ball()

    elif key in ("r", "R") and state["game_over"]:
        restart_game(canvas, ball_obj, paddle_obj, score_text,
                     lives_text, message_text, sub_text)


def restart_game(canvas, ball_obj, paddle_obj, score_text,
                 lives_text, message_text, sub_text):
    """
    Reset ALL game state and redraw the brick grid so the player
    can start a fresh round without restarting the program.
    """
    # Clear any remaining bricks from the canvas
    for brick_id in list(state["bricks"]):
        canvas.delete(brick_id)

    # Reset state values
    state["score"]    = 0
    state["lives"]    = 3
    state["game_over"] = False
    state["win"]      = False
    state["paddle_x"] = WINDOW_WIDTH / 2 - PADDLE_WIDTH / 2

    # Rebuild bricks and reset ball
    create_bricks(canvas)
    reset_ball(canvas, ball_obj)

    # Clear overlay messages
    canvas.itemconfig(message_text, text="")
    canvas.itemconfig(sub_text,
                      text="Press SPACE to launch the ball",
                      fill="#7777aa")


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def main():
    """
    Build the tkinter window, create all canvas objects, wire up
    event bindings, then start the animation loop.
    """
    # ── Window & Canvas ────────────────────────────────────────────
    root = tk.Tk()
    root.title("Breakout – Code in Place Final Project")
    root.resizable(False, False)

    canvas = tk.Canvas(
        root,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        bg=BACKGROUND,
        highlightthickness=0
    )
    canvas.pack()

    # ── Background decorative dots (purely cosmetic) ───────────────
    for _ in range(60):
        sx = random.randint(0, WINDOW_WIDTH)
        sy = random.randint(0, WINDOW_HEIGHT)
        r  = random.choice([1, 1, 1, 2])
        canvas.create_oval(sx, sy, sx + r, sy + r,
                   fill="#ffffff", outline="")

    # ── Bricks ─────────────────────────────────────────────────────
    create_bricks(canvas)

    # ── Paddle ─────────────────────────────────────────────────────
    paddle_obj = canvas.create_rectangle(
        state["paddle_x"], PADDLE_Y,
        state["paddle_x"] + PADDLE_WIDTH, PADDLE_Y + PADDLE_HEIGHT,
        fill=PADDLE_COLOR, outline="#aaaaff", width=2
    )

    # ── Ball ───────────────────────────────────────────────────────
    ball_obj = canvas.create_oval(
        state["ball_x"] - BALL_RADIUS,
        state["ball_y"] - BALL_RADIUS,
        state["ball_x"] + BALL_RADIUS,
        state["ball_y"] + BALL_RADIUS,
        fill=BALL_COLOR, outline="#ccccff", width=1
    )

    # ── HUD: score & lives ─────────────────────────────────────────
    score_text = canvas.create_text(
        10, 10, anchor="nw",
        text="Score: 0",
        fill="#e0e0ff", font=("Courier", 13, "bold")
    )
    lives_text = canvas.create_text(
        WINDOW_WIDTH - 10, 10, anchor="ne",
        text="Lives: 3",
        fill="#e0e0ff", font=("Courier", 13, "bold")
    )

    # ── Overlay messages (game over / win / hints) ─────────────────
    message_text = canvas.create_text(
        WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 30,
        text="",
        fill="#ffffff", font=("Courier", 30, "bold")
    )
    sub_text = canvas.create_text(
        WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 10,
        text="Press SPACE to launch the ball",
        fill="#7777aa", font=("Courier", 12)
    )

    # ── Event bindings ─────────────────────────────────────────────
    canvas.bind("<Motion>", on_mouse_move)
    root.bind("<KeyPress>", lambda event: on_key_press(
        event, canvas, ball_obj, paddle_obj,
        score_text, lives_text, message_text, sub_text
    ))

    # ── Start the animation loop ───────────────────────────────────
    game_loop(canvas, ball_obj, paddle_obj,
              score_text, lives_text, message_text, sub_text)

    root.mainloop()


# Run the game
if __name__ == "__main__":
    main()
