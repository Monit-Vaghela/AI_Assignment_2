
"""
River and Stones Game - AI Agent Framework

This module provides the base agent implementations and factory function.
The student implementation is in student_agent.py for better organization.

Game Rules Summary:
- Two players: Circle (red) and Square (blue)
- Pieces can be stones or rivers (horizontal/vertical)
- Goal: Get 4 of your stones into opponent's scoring area
- Actions: move, push, flip (stone↔river), rotate (river orientation)
- Rivers allow flow-based movement to distant locations
"""

import random
import copy
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod

# ==================== GAME UTILITIES ====================
# These functions help agents understand and manipulate the game state

def in_bounds(x: int, y: int, rows: int, cols: int) -> bool:
    """Check if coordinates are within board boundaries."""
    return 0 <= x < cols and 0 <= y < rows

def score_cols_for(cols: int) -> List[int]:
    """Get the column indices for scoring areas."""
    w = 4
    start = max(0, (cols - w) // 2)
    return list(range(start, start + w))

def top_score_row() -> int:
    """Get the row index for Circle's scoring area."""
    return 2

def bottom_score_row(rows: int) -> int:
    """Get the row index for Square's scoring area."""
    return rows - 3

def is_opponent_score_cell(x: int, y: int, player: str, rows: int, cols: int, score_cols: List[int]) -> bool:
    """Check if a cell is in the opponent's scoring area."""
    if player == "circle":
        return (y == bottom_score_row(rows)) and (x in score_cols)
    else:
        return (y == top_score_row()) and (x in score_cols)

def is_own_score_cell(x: int, y: int, player: str, rows: int, cols: int, score_cols: List[int]) -> bool:
    """Check if a cell is in the player's own scoring area."""
    if player == "circle":
        return (y == top_score_row()) and (x in score_cols)
    else:
        return (y == bottom_score_row(rows)) and (x in score_cols)

def get_opponent(player: str) -> str:
    """Get the opponent player identifier."""
    return "square" if player == "circle" else "circle"

# ==================== RIVER FLOW SIMULATION ====================

def agent_river_flow(board, rx: int, ry: int, sx: int, sy: int, player: str, 
                    rows: int, cols: int, score_cols: List[int], river_push: bool = False) -> List[Tuple[int, int]]:
    """
    Simulate river flow from a given position.
    
    Args:
        board: Current board state
        rx, ry: River entry point
        sx, sy: Source position (where piece is moving from)
        player: Current player
        rows, cols: Board dimensions
        score_cols: Scoring column indices
        river_push: Whether this is for a river push move
    
    Returns:
        List of (x, y) coordinates where the piece can end up via river flow
    """
    destinations = []
    visited = set()
    queue = [(rx, ry)]
    
    while queue:
        x, y = queue.pop(0)
        if (x, y) in visited or not in_bounds(x, y, rows, cols):
            continue
        visited.add((x, y))
        
        cell = board[y][x]
        if river_push and x == rx and y == ry:
            cell = board[sy][sx]
            
        if cell is None:
            if is_opponent_score_cell(x, y, player, rows, cols, score_cols):
                # Block entering opponent score cell
                pass
            else:
                destinations.append((x, y))
            continue
            
        if getattr(cell, "side", "stone") != "river":
            continue
            
        # River flow directions
        dirs = [(1, 0), (-1, 0)] if cell.orientation == "horizontal" else [(0, 1), (0, -1)]
        
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            while in_bounds(nx, ny, rows, cols):
                if is_opponent_score_cell(nx, ny, player, rows, cols, score_cols):
                    break
                    
                next_cell = board[ny][nx]
                if next_cell is None:
                    destinations.append((nx, ny))
                    nx += dx
                    ny += dy
                    continue
                    
                if nx == sx and ny == sy:
                    nx += dx
                    ny += dy
                    continue
                    
                if getattr(next_cell, "side", "stone") == "river":
                    queue.append((nx, ny))
                    break
                break
    
    # Remove duplicates
    unique_destinations = []
    seen = set()
    for d in destinations:
        if d not in seen:
            seen.add(d)
            unique_destinations.append(d)
    
    return unique_destinations

# ==================== MOVE VALIDATION AND GENERATION ====================

def agent_compute_valid_moves(board, sx: int, sy: int, player: str, rows: int, cols: int, score_cols: List[int]) -> Dict[str, Any]:
    """
    Compute all valid moves for a piece at position (sx, sy).
    
    Returns:
        Dictionary with 'moves' (set of coordinates) and 'pushes' (list of tuples)
    """
    if not in_bounds(sx, sy, rows, cols):
        return {'moves': set(), 'pushes': []}
        
    piece = board[sy][sx]
    if piece is None or piece.owner != player:
        return {'moves': set(), 'pushes': []}
    
    moves = set()
    pushes = []
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    
    for dx, dy in directions:
        tx, ty = sx + dx, sy + dy
        if not in_bounds(tx, ty, rows, cols):
            continue
            
        # Block moving into opponent score cell
        if is_opponent_score_cell(tx, ty, player, rows, cols, score_cols):
            continue
            
        target = board[ty][tx]
        
        if target is None:
            # Empty cell - direct move
            moves.add((tx, ty))
        elif getattr(target, "side", "stone") == "river":
            # River - compute flow destinations
            flow = agent_river_flow(board, tx, ty, sx, sy, player, rows, cols, score_cols)
            for dest in flow:
                moves.add(dest)
        else:
            # Occupied by stone - check push possibility
            if getattr(piece, "side", "stone") == "stone":
                # Stone pushing stone
                px, py = tx + dx, ty + dy
                if (in_bounds(px, py, rows, cols) and 
                    board[py][px] is None and 
                    not is_opponent_score_cell(px, py, player, rows, cols, score_cols)):
                    pushes.append(((tx, ty), (px, py)))
            else:
                # River pushing - compute flow for pushed piece
                flow = agent_river_flow(board, tx, ty, sx, sy, player, rows, cols, score_cols, river_push=True)
                for dest in flow:
                    if not is_opponent_score_cell(dest[0], dest[1], player, rows, cols, score_cols):
                        pushes.append(((tx, ty), dest))
    
    return {'moves': moves, 'pushes': pushes}

# ==================== MOVE APPLICATION (FOR SIMULATION) ====================

def agent_apply_move(board, move: Dict[str, Any], player: str, rows: int, cols: int, score_cols: List[int]) -> Tuple[bool, str]:
    """
    Apply a move to a board copy for simulation purposes.
    
    Args:
        board: Board state to modify
        move: Move dictionary
        player: Current player
        rows, cols: Board dimensions
        score_cols: Scoring column indices
    
    Returns:
        (success: bool, message: str)
    """
    action = move.get("action")
    
    if action == "move":
        return _apply_move_action(board, move, player, rows, cols, score_cols)
    elif action == "push":
        return _apply_push_action(board, move, player, rows, cols, score_cols)
    elif action == "flip":
        return _apply_flip_action(board, move, player, rows, cols, score_cols)
    elif action == "rotate":
        return _apply_rotate_action(board, move, player, rows, cols, score_cols)
    
    return False, "unknown action"

def _apply_move_action(board, move, player, rows, cols, score_cols):
    """Apply a move action."""
    fr = move.get("from")
    to = move.get("to")
    if not fr or not to:
        return False, "bad move format"
    
    fx, fy = int(fr[0]), int(fr[1])
    tx, ty = int(to[0]), int(to[1])
    
    if not in_bounds(fx, fy, rows, cols) or not in_bounds(tx, ty, rows, cols):
        return False, "out of bounds"
    
    if is_opponent_score_cell(tx, ty, player, rows, cols, score_cols):
        return False, "cannot move into opponent score cell"
    
    piece = board[fy][fx]
    if piece is None or piece.owner != player:
        return False, "invalid piece"
    
    if board[ty][tx] is None:
        # Simple move
        board[ty][tx] = piece
        board[fy][fx] = None
        return True, "moved"
    
    # Move with push
    pushed_to = move.get("pushed_to")
    if not pushed_to:
        return False, "destination occupied; pushed_to required"
    
    ptx, pty = int(pushed_to[0]), int(pushed_to[1])
    dx, dy = tx - fx, ty - fy
    
    if (ptx, pty) != (tx + dx, ty + dy):
        return False, "invalid pushed_to"
    
    if not in_bounds(ptx, pty, rows, cols):
        return False, "pushed_to out of bounds"
    
    if is_opponent_score_cell(ptx, pty, player, rows, cols, score_cols):
        return False, "cannot push into opponent score"
    
    if board[pty][ptx] is not None:
        return False, "pushed_to not empty"
    
    board[pty][ptx] = board[ty][tx]
    board[ty][tx] = piece
    board[fy][fx] = None
    return True, "moved with push"

def _apply_push_action(board, move, player, rows, cols, score_cols):
    """Apply a push action."""
    fr = move.get("from")
    to = move.get("to")
    pushed_to = move.get("pushed_to")
    
    if not fr or not to or not pushed_to:
        return False, "bad push format"
    
    fx, fy = int(fr[0]), int(fr[1])
    tx, ty = int(to[0]), int(to[1])
    px, py = int(pushed_to[0]), int(pushed_to[1])
    
    if (is_opponent_score_cell(tx, ty, player, rows, cols, score_cols) or
        is_opponent_score_cell(px, py, player, rows, cols, score_cols)):
        return False, "push would move into opponent score cell"
    
    if not (in_bounds(fx, fy, rows, cols) and 
            in_bounds(tx, ty, rows, cols) and 
            in_bounds(px, py, rows, cols)):
        return False, "out of bounds"
    
    piece = board[fy][fx]
    if piece is None or piece.owner != player:
        return False, "invalid piece"
    
    if board[ty][tx] is None:
        return False, "'to' must be occupied"
    
    if board[py][px] is not None:
        return False, "pushed_to not empty"
    
    board[py][px] = board[ty][tx]
    board[ty][tx] = board[fy][fx]
    board[fy][fx] = None
    return True, "pushed"

def _apply_flip_action(board, move, player, rows, cols, score_cols):
    """Apply a flip action."""
    fr = move.get("from")
    if not fr:
        return False, "bad flip format"
    
    fx, fy = int(fr[0]), int(fr[1])
    piece = board[fy][fx]
    
    if piece is None or piece.owner != player:
        return False, "invalid piece"
    
    if piece.side == "stone":
        # Stone to river
        orientation = move.get("orientation")
        if orientation not in ("horizontal", "vertical"):
            return False, "stone->river needs orientation"
        
        # Check if new river would allow flow into opponent score
        board[fy][fx].side = "river"
        board[fy][fx].orientation = orientation
        flow = agent_river_flow(board, fx, fy, fx, fy, player, rows, cols, score_cols)
        
        # Revert for safety check
        board[fy][fx].side = "stone"
        board[fy][fx].orientation = None
        
        for dx, dy in flow:
            if is_opponent_score_cell(dx, dy, player, rows, cols, score_cols):
                return False, "flip would allow flow into opponent score cell"
        
        # Apply flip
        board[fy][fx].side = "river"
        board[fy][fx].orientation = orientation
        return True, "flipped to river"
    else:
        # River to stone
        board[fy][fx].side = "stone"
        board[fy][fx].orientation = None
        return True, "flipped to stone"

def _apply_rotate_action(board, move, player, rows, cols, score_cols):
    """Apply a rotate action."""
    fr = move.get("from")
    if not fr:
        return False, "bad rotate format"
    
    fx, fy = int(fr[0]), int(fr[1])
    piece = board[fy][fx]
    
    if piece is None or piece.owner != player or piece.side != "river":
        return False, "invalid rotate"
    
    # Try rotation
    old_orientation = piece.orientation
    piece.orientation = "horizontal" if piece.orientation == "vertical" else "vertical"
    
    # Check flow safety after rotation
    flow = agent_river_flow(board, fx, fy, fx, fy, player, rows, cols, score_cols)
    
    for dx, dy in flow:
        if is_opponent_score_cell(dx, dy, player, rows, cols, score_cols):
            # Revert rotation
            piece.orientation = old_orientation
            return False, "rotate would allow flow into opponent score cell"
    
    return True, "rotated"

# ==================== BASE AGENT CLASS ====================

class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    Students should inherit from this class and implement the required methods.
    """
    
    def __init__(self, player: str):
        """
        Initialize agent.
        
        Args:
            player: Either "circle" or "square"
        """
        self.player = player
        self.opponent = get_opponent(player)
        self.moves = 0
    
    @abstractmethod
    def choose(self, board: List[List[Any]], rows: int, cols: int, score_cols: List[int], current_player_time: float, opponent_time: float, weights : Dict[str, float]) -> Optional[Dict[str, Any]]:
        """
        Choose the best move for the current board state.
        
        Args:
            board: 2D list representing the game board
            rows, cols: Board dimensions
            score_cols: List of column indices for scoring areas
            current_player_time : Remaining time for this player (in seconds)
            opponent_time : Remaining time for the opponent (in seconds)
        
        Returns:
            Dictionary representing the chosen move, or None if no moves available
            
        Move format examples:
            {"action": "move", "from": [x, y], "to": [x2, y2]}
            {"action": "push", "from": [x, y], "to": [x2, y2], "pushed_to": [x3, y3]}
            {"action": "flip", "from": [x, y], "orientation": "horizontal"}  # stone->river
            {"action": "flip", "from": [x, y]}  # river->stone
            {"action": "rotate", "from": [x, y]}  # rotate river
        """
        pass

    def get_river_flow_destinations(self, board: List[List[Any]], rx: int, ry: int, sx: int, sy: int,
                                    player: str, rows: int, cols: int, score_cols: List[int],
                                    river_push: bool = False) -> List[Tuple[int, int]]:
        """
        Calculate all possible destinations when entering a river at (rx, ry).

        Args:
            board: Current board state
            rx, ry: River entry point
            sx, sy: Source position (where piece is coming from)
            player: Player making the move
            rows, cols: Board dimensions
            score_cols: Scoring column indices
            river_push: Whether this is for a river push move

        Returns:
            List of (x, y) coordinates where piece can end up
        """
        destinations = []
        visited = set()
        queue = [(rx, ry)]

        while queue:
            x, y = queue.pop(0)
            if (x, y) in visited or not in_bounds(x, y, rows, cols):
                continue
            visited.add((x, y))

            cell = board[y][x]
            if river_push and x == rx and y == ry:
                cell = board[sy][sx]

            if cell is None:
                if is_opponent_score_cell(x, y, player, rows, cols, score_cols):
                    # Block entering opponent score
                    pass
                else:
                    destinations.append((x, y))
                continue

            if cell.side != "river":
                continue

            # River flow directions
            dirs = [(1, 0), (-1, 0)] if cell.orientation == "horizontal" else [(0, 1), (0, -1)]

            for dx, dy in dirs:
                nx, ny = x + dx, y + dy
                while in_bounds(nx, ny, rows, cols):
                    if is_opponent_score_cell(nx, ny, player, rows, cols, score_cols):
                        break

                    next_cell = board[ny][nx]
                    if next_cell is None:
                        destinations.append((nx, ny))
                        nx += dx
                        ny += dy
                        continue

                    if nx == sx and ny == sy:
                        nx += dx
                        ny += dy
                        continue

                    if next_cell.side == "river":
                        queue.append((nx, ny))
                        break
                    break

        # Remove duplicates
        unique_destinations = []
        seen = set()
        for d in destinations:
            if d not in seen:
                seen.add(d)
                unique_destinations.append(d)

        return unique_destinations

    def generate_all_moves(self, board: List[List[Any]], player: str, rows: int, cols: int, score_cols: List[int]) -> List[Dict[str, Any]]:
        """
        Generate all legal moves for the current player.

        Args:
            board: Current board state
            player: Current player ("circle" or "square")
            rows, cols: Board dimensions
            score_cols: Scoring column indices

        Returns:
            List of all valid move dictionaries
        """
        all_moves = []
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]

        for y in range(rows):
            for x in range(cols):
                piece = board[y][x]
                if not piece or piece.owner != player:
                    continue

                if piece.side == "stone":
                    # === STONE MOVES ===
                    for dx, dy in directions:
                        nx, ny = x + dx, y + dy
                        if not in_bounds(nx, ny, rows, cols):
                            continue

                        # Cannot move into opponent's score area
                        if is_opponent_score_cell(nx, ny, player, rows, cols, score_cols):
                            continue

                        target = board[ny][nx]

                        if target is None:
                            # Simple move to empty cell
                            all_moves.append({
                                "action": "move",
                                "from": [x, y],
                                "to": [nx, ny]
                            })

                        elif target.side == "river":
                            # Move through river flow
                            flow_destinations = self.get_river_flow_destinations(
                                board, nx, ny, x, y, player, rows, cols, score_cols
                            )
                            for dest_x, dest_y in flow_destinations:
                                all_moves.append({
                                    "action": "move",
                                    "from": [x, y],
                                    "to": [dest_x, dest_y]
                                })

                        else:
                            # Target is a stone - check if we can push it
                            px, py = nx + dx, ny + dy
                            if (in_bounds(px, py, rows, cols) and
                                    board[py][px] is None and
                                    not is_opponent_score_cell(px, py, target.owner, rows, cols, score_cols)):
                                all_moves.append({
                                    "action": "push",
                                    "from": [x, y],
                                    "to": [nx, ny],
                                    "pushed_to": [px, py]
                                })

                    # === STONE TO RIVER FLIPS ===
                    for orientation in ["horizontal", "vertical"]:
                        # Check if this flip would be valid (doesn't create flow into opponent score)
                        all_moves.append({
                            "action": "flip",
                            "from": [x, y],
                            "orientation": orientation
                        })

                else:  # piece.side == "river"
                    # === RIVER MOVES ===
                    for dx, dy in directions:
                        nx, ny = x + dx, y + dy
                        if not in_bounds(nx, ny, rows, cols):
                            continue

                        # Cannot move into opponent's score area
                        if is_opponent_score_cell(nx, ny, player, rows, cols, score_cols):
                            continue

                        target = board[ny][nx]

                        if target is None:
                            # Simple move to empty cell
                            all_moves.append({
                                "action": "move",
                                "from": [x, y],
                                "to": [nx, ny]
                            })

                        elif target.side == "river":
                            # Move through river flow
                            flow_destinations = self.get_river_flow_destinations(
                                board, nx, ny, x, y, player, rows, cols, score_cols
                            )
                            for dest_x, dest_y in flow_destinations:
                                all_moves.append({
                                    "action": "move",
                                    "from": [x, y],
                                    "to": [dest_x, dest_y]
                                })

                        else:
                            # Target is a stone - river can push with flow
                            flow_destinations = self.get_river_flow_destinations(
                                board, nx, ny, x, y, target.owner, rows, cols, score_cols, river_push=True
                            )
                            for dest_x, dest_y in flow_destinations:
                                if not is_opponent_score_cell(dest_x, dest_y, target.owner, rows, cols, score_cols):
                                    all_moves.append({
                                        "action": "push",
                                        "from": [x, y],
                                        "to": [nx, ny],
                                        "pushed_to": [dest_x, dest_y]
                                    })

                    # === RIVER TO STONE FLIP ===
                    all_moves.append({
                        "action": "flip",
                        "from": [x, y]
                    })

                    # === RIVER ROTATION ===
                    new_orientation = "vertical" if piece.orientation == "horizontal" else "horizontal"

                    all_moves.append({
                        "action": "rotate",
                        "from": [x, y]
                    })

        return all_moves

    def simulate_move(self, board: List[List[Any]], move: Dict[str, Any], player: str, rows: int, cols: int,
                      score_cols: List[int]) -> Tuple[bool, Any]:
        """
        Simulate a move on a copy of the board.

        Args:
            board: Current board state
            move: Move to simulate
            player: Player making the move
            rows, cols: Board dimensions
            score_cols: Scoring column indices

        Returns:
            (success: bool, new_board_state or error_message)
        """
        # Import the game engine's move validation function
        try:
            from gameEngine import validate_and_apply_move
            board_copy = copy.deepcopy(board)
            success, message = validate_and_apply_move(board_copy, move, player, rows, cols, score_cols)
            return success, board_copy if success else message
        except ImportError:
            # Fallback to basic simulation if game engine not available
            return True, copy.deepcopy(board)

# ==================== EXAMPLE AGENT IMPLEMENTATIONS ====================

class RandomAgent(BaseAgent):
    """
    Simple random agent that chooses moves randomly.
    This serves as a baseline and example implementation.
    """
    
    def choose(self, board: List[List[Any]], rows: int, cols: int, score_cols: List[int], current_player_time: float, opponent_time: float, weights : Dict[str, float]) -> Optional[Dict[str, Any]]:
        moves = self.generate_all_moves(board, self.player, rows, cols, score_cols)
        if not moves:
            return None
        return random.choice(moves)

# ==================== STUDENT AGENT IMPORT ====================

try:
    from student_agent import StudentAgent
except ImportError:
    print("Warning: student_agent.py not found. Creating placeholder StudentAgent.")
    
    class StudentAgent(BaseAgent):
        """Placeholder StudentAgent - implement in student_agent.py"""
        
        def choose(self, board: List[List[Any]], rows: int, cols: int, score_cols: List[int], current_player_time: float, opponent_time: float, weights : Dict[str, float]) -> Optional[Dict[str, Any]]:
            moves = self.generate_all_moves(board, self.player,rows, cols, score_cols)
            return random.choice(moves) if moves else None

# ==================== AGENT FACTORY ====================

from student_agent import StudentAgent

class RandomAgent(BaseAgent):
    def choose(self, board, rows, cols, score_cols, t1, t2, weights):
        moves = self.generate_all_moves(board, self.player, rows, cols, score_cols)
        return random.choice(moves) if moves else None

class GreedyAgent(BaseAgent):

    def minimax(self, board, depth, alpha, beta, maximizing, player, rows, cols, score_cols):
        if depth == 0:
            return self.advanced_evaluate_board(board, player, rows, cols, score_cols), None

        current_player = player if maximizing else get_opponent(player)
        moves = self.generate_all_moves(board, current_player, rows, cols, score_cols)

        if not moves:
            # No moves available -> terminal
            return self.advanced_evaluate_board(board, player, rows, cols, score_cols), None

        best_move = None

        if maximizing:
            max_eval = float("-inf")
            for move in moves:
                ok, new_board = self.simulate_move(board, move, current_player, rows, cols, score_cols)
                if not ok:
                    continue
                eval_score, _ = self.minimax(new_board, depth - 1, alpha, beta, False, player, rows, cols, score_cols)
                if move['action'] == 'flip':
                    eval_score -= 2
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break
            return max_eval, best_move

        else:  # minimizing opponent
            min_eval = float("inf")
            for move in moves:
                ok, new_board = self.simulate_move(board, move, current_player, rows, cols, score_cols)
                if not ok:
                    continue
                eval_score, _ = self.minimax(new_board, depth - 1, alpha, beta, True, player, rows, cols, score_cols)
                if move['action'] == 'flip':
                    eval_score -= 1
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break
            return min_eval, best_move

    def choose(self, board, rows, cols, score_cols, t1, t2, weights):
        # print("YOU ARE PLAYING AGAINST DEPTH ", 3)
        moves = self.generate_all_moves(board, self.player, rows, cols, score_cols)
        if self.moves < 10:
            self.moves += 1
            return random.choice(moves)
        depth = 3  # start small; increase if performance allows
        _, best_move = self.minimax(board, depth, float("-inf"), float("inf"), True, self.player, rows, cols,
                                    score_cols)
        return best_move

        '''best_move = moves[0]
        max_score = float('-inf')
        for move in moves:
            ok, new_board = self.simulate_move(board, move, self.player, rows, cols, score_cols)
            if ok:
                score = self.advanced_evaluate_board(new_board, self.player, rows, cols, score_cols)
                if score > max_score:
                    max_score = score
                    best_move = move
        return best_move'''


    """
    Advanced Evaluation Function for River and Stones Game

    This evaluation function considers multiple strategic factors:
    1. Stones in scoring areas (highest priority)
    2. Stones that can reach scoring areas in one move
    3. Positional advancement toward opponent's scoring area
    4. Control of key board regions
    5. River network connectivity and flow potential
    6. Defensive positioning to block opponent
    7. Piece mobility and tactical opportunities
    """

    def count_stones_in_scoring_area(self, board: List[List[Any]], player: str, rows: int, cols: int,
                                     score_cols: List[int]) -> int:
        """Count stones in player's scoring area."""
        count = 0
        if player == "circle":
            score_row = 2  # top_score_row()
        else:
            score_row = rows - 3  # bottom_score_row(rows)

        for x in score_cols:
            if 0 <= x < cols and 0 <= score_row < rows:
                piece = board[score_row][x]
                if piece and piece.owner == player and piece.side == "stone":
                    count += 1
        return count

    def count_stones_reachable_in_one(self, board: List[List[Any]], player: str, rows: int, cols: int,
                                      score_cols: List[int]) -> int:
        """Count stones that can reach scoring area in one move."""
        count = 0

        if player == "circle":
            target_row = 2
        else:
            target_row = rows - 3

        for y in range(rows):
            for x in range(cols):
                piece = board[y][x]
                if not piece or piece.owner != player or piece.side != "stone":
                    continue

                # Skip if already in scoring area
                if y == target_row and x in score_cols:
                    continue

                # Check if can reach scoring area in one move
                moves = self.get_valid_moves_for_piece(board, x, y, player, rows, cols, score_cols)
                for move in moves:
                    if move.get("action") in ["move", "push"]:
                        dest = move.get("to") or move.get("pushed_to")
                        if dest and dest[1] == target_row and dest[0] in score_cols:
                            count += 1
                            break

                # Check if river piece can flip to stone in scoring area
                if piece.side == "river" and y == target_row and x in score_cols:
                    count += 1

        return count

    def count_stones_reachable_in_two(self, board: List[List[Any]], player: str, rows: int, cols: int,
                                      score_cols: List[int]) -> int:
        """Count stones that can reach scoring area in two moves."""
        count = 0

        if player == "circle":
            target_row = 2
        else:
            target_row = rows - 3

        for y in range(rows):
            for x in range(cols):
                piece = board[y][x]
                if not piece or piece.owner != player or piece.side != "stone":
                    continue

                # Skip if already in scoring area or reachable in one
                if y == target_row and x in score_cols:
                    continue
                if self.can_reach_in_moves(board, x, y, player, rows, cols, score_cols, 1):
                    continue

                # Check if reachable in two moves
                if self.can_reach_in_moves(board, x, y, player, rows, cols, score_cols, 2):
                    count += 1

        return count

    def can_reach_in_moves(self, board: List[List[Any]], start_x: int, start_y: int, player: str,
                           rows: int, cols: int, score_cols: List[int], max_moves: int) -> bool:
        """Check if a piece can reach scoring area within max_moves."""
        if max_moves <= 0:
            return False

        if player == "circle":
            target_row = 2
        else:
            target_row = rows - 3

        # BFS to find if scoring area is reachable
        queue = [(start_x, start_y, 0)]  # (x, y, moves_used)
        visited = set()

        while queue:
            x, y, moves = queue.pop(0)

            if moves > max_moves:
                continue

            if (x, y, moves) in visited:
                continue
            visited.add((x, y, moves))

            # Check if at target
            if y == target_row and x in score_cols:
                return True

            if moves < max_moves:
                # Try all moves from this position
                temp_board = copy.deepcopy(board)
                if temp_board[y][x] and temp_board[y][x].owner == player:
                    valid_moves = self.get_valid_moves_for_piece(temp_board, x, y, player, rows, cols, score_cols)
                    for move in valid_moves:
                        if move.get("action") in ["move", "push"]:
                            dest = move.get("to")
                            if dest:
                                queue.append((dest[0], dest[1], moves + 1))

        return False

    def evaluate_positional_advancement(self, board: List[List[Any]], player: str, rows: int, cols: int,
                                        score_cols: List[int]) -> float:
        """Evaluate how advanced pieces are toward opponent's scoring area."""
        advancement = 0.0

        for y in range(rows):
            for x in range(cols):
                piece = board[y][x]
                if piece and piece.owner == player and piece.side == "stone":
                    if player == "circle":
                        # Circle wants to reach row 2, so higher y values are closer
                        distance_from_start = abs(y - (rows - 4))  # Start around row 9-10
                        advancement += max(0, 10 - distance_from_start)
                    else:
                        # Square wants to reach row 10, so lower y values are closer
                        distance_from_start = abs(y - 4)  # Start around row 3-4
                        advancement += max(0, 10 - distance_from_start)

        return advancement

    def evaluate_board_control(self, board: List[List[Any]], player: str, rows: int, cols: int,
                               score_cols: List[int]) -> float:
        """Evaluate control of key board regions."""
        control = 0.0

        # Central columns are valuable
        center_cols = [c for c in range(cols // 3, (2 * cols) // 3)]

        # Key rows (middle third of board)
        key_rows = list(range(rows // 3, (2 * rows) // 3))

        for y in key_rows:
            for x in center_cols:
                piece = board[y][x]
                if piece and piece.owner == player:
                    control += 2.0  # Bonus for controlling center

        # Score column control
        for x in score_cols:
            for y in range(rows):
                piece = board[y][x]
                if piece and piece.owner == player:
                    control += 1.5  # Bonus for controlling scoring columns

        return control

    def evaluate_defensive_positioning(self, board: List[List[Any]], player: str, rows: int, cols: int,
                                       score_cols: List[int]) -> float:
        """Evaluate defensive positioning to block opponent advancement."""
        defense = 0.0
        opponent = "square" if player == "circle" else "circle"

        # Get opponent's target scoring row
        if opponent == "circle":
            opponent_target_row = 2
            defensive_rows = [3, 4, 5]  # Rows to defend
        else:
            opponent_target_row = rows - 3
            defensive_rows = [rows - 6, rows - 5, rows - 4]

        # Check for defensive pieces near scoring columns
        for row in defensive_rows:
            for x in score_cols:
                # Check surrounding positions
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        nx, ny = x + dx, row + dy
                        if 0 <= nx < cols and 0 <= ny < rows:
                            piece = board[ny][nx]
                            if piece and piece.owner == player:
                                defense += 3.0 - abs(dx) - abs(dy)  # Closer is better

        return defense

    def evaluate_river_network(self, board: List[List[Any]], player: str, rows: int, cols: int,
                               score_cols: List[int]) -> float:
        """Evaluate the value of river networks for flow-based movement."""
        river_value = 0.0

        # Find all rivers
        rivers = []
        for y in range(rows):
            for x in range(cols):
                piece = board[y][x]
                if piece and piece.owner == player and piece.side == "river":
                    rivers.append((x, y))

        # Evaluate connectivity and strategic positioning
        for rx, ry in rivers:
            # Base value for having a river
            river_value += 5.0

            # Bonus if river is in scoring columns
            if rx in score_cols:
                river_value += 10.0

            # Bonus if river connects to useful areas
            flow_destinations = self.get_river_flow_destinations(board, rx, ry, rx, ry, player, rows, cols, score_cols)

            # Value destinations near scoring area
            for fx, fy in flow_destinations:
                if player == "circle":
                    distance_to_score = abs(fy - 2)
                else:
                    distance_to_score = abs(fy - (rows - 3))

                river_value += max(0, 5 - distance_to_score)

                # Bonus if flow reaches scoring columns
                if fx in score_cols:
                    river_value += 3.0

        return river_value

    def count_total_mobility(self, board: List[List[Any]], player: str, rows: int, cols: int, score_cols: List[int]) -> int:
        """Count total number of legal moves available."""
        total_moves = 0

        for y in range(rows):
            for x in range(cols):
                piece = board[y][x]
                if piece and piece.owner == player:
                    moves = self.get_valid_moves_for_piece(board, x, y, player, rows, cols, score_cols)
                    total_moves += len(moves)

        return total_moves

    def count_push_opportunities(self, board: List[List[Any]], player: str, rows: int, cols: int,
                                 score_cols: List[int]) -> int:
        """Count opportunities to push opponent pieces away from strategic positions."""
        push_count = 0
        opponent = "square" if player == "circle" else "circle"

        for y in range(rows):
            for x in range(cols):
                piece = board[y][x]
                if piece and piece.owner == player:
                    moves = self.get_valid_moves_for_piece(board, x, y, player, rows, cols, score_cols)
                    for move in moves:
                        if move.get("action") == "push":
                            # Check if we're pushing opponent away from valuable position
                            target_pos = move.get("to")
                            if target_pos:
                                target_piece = board[target_pos[1]][target_pos[0]]
                                if target_piece and target_piece.owner == opponent:
                                    # Valuable if pushing away from scoring columns or key positions
                                    if target_pos[0] in score_cols:
                                        push_count += 2
                                    else:
                                        push_count += 1

        return push_count

    # Helper functions (simplified versions of the game engine functions)

    def get_valid_moves_for_piece(self, board, x: int, y: int, player: str, rows: int, cols: int, score_cols: List[int]) -> \
    List[Dict[str, Any]]:
        """Generate valid moves for a specific piece."""
        moves = []
        piece = board[y][x]

        if not piece or piece.owner != player:
            return moves

        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]

        if piece.side == "stone":
            # Stone movement and pushes
            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < cols and 0 <= ny < rows):
                    continue

                if is_opponent_score_cell(nx, ny, player, rows, cols, score_cols):
                    continue

                if board[ny][nx] is None:
                    moves.append({"action": "move", "from": [x, y], "to": [nx, ny]})
                else:
                    # Push move
                    px, py = nx + dx, ny + dy
                    if (0 <= px < cols and 0 <= py < rows and
                            board[py][px] is None and
                            not is_opponent_score_cell(px, py, player, rows, cols, score_cols)):
                        moves.append({"action": "push", "from": [x, y], "to": [nx, ny], "pushed_to": [px, py]})

            # Flip to river
            for orientation in ["horizontal", "vertical"]:
                moves.append({"action": "flip", "from": [x, y], "orientation": orientation})

        else:  # River piece
            # River movement (simplified)
            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                if (0 <= nx < cols and 0 <= ny < rows and
                        board[ny][nx] is None and
                        not is_opponent_score_cell(nx, ny, player, rows, cols, score_cols)):
                    moves.append({"action": "move", "from": [x, y], "to": [nx, ny]})

            # Flip to stone and rotate
            moves.append({"action": "flip", "from": [x, y]})
            moves.append({"action": "rotate", "from": [x, y]})

        return moves

    def is_opponent_score_cell(self, x: int, y: int, player: str, rows: int, cols: int, score_cols: List[int]) -> bool:
        """Check if cell is in opponent's scoring area."""
        if player == "circle":
            return (y == rows - 3) and (x in score_cols)
        else:
            return (y == 2) and (x in score_cols)

    def advanced_evaluate_board(self, board: List[List[Any]], player: str, rows: int, cols: int,
                                score_cols: List[int]) -> float:
        """
        Advanced evaluation function that considers multiple strategic factors.

        Args:
            board: Current board state
            player: Player to evaluate for ("circle" or "square")
            rows, cols: Board dimensions
            score_cols: Scoring column indices

        Returns:
            Evaluation score (higher = better for player)
        """
        opponent = "square" if player == "circle" else "circle"
        score = 0.0

        # === CRITICAL FACTORS (High Weight) ===

        # 1. Stones in scoring areas (1000 points each)
        player_scoring_stones = self.count_stones_in_scoring_area(board, player, rows, cols, score_cols)
        opponent_scoring_stones = self.count_stones_in_scoring_area(board, opponent, rows, cols, score_cols)
        score += player_scoring_stones * 1000
        score -= opponent_scoring_stones * 1000

        # 2. Stones that can reach scoring area in one move (500 points each)
        player_reachable = self.count_stones_reachable_in_one(board, player, rows, cols, score_cols)
        opponent_reachable = self.count_stones_reachable_in_one(board, opponent, rows, cols, score_cols)
        score += player_reachable * 500
        score -= opponent_reachable * 500

        # 3. Stones that can reach scoring area in two moves (100 points each)
        player_two_move = self.count_stones_reachable_in_two(board, player, rows, cols, score_cols)
        opponent_two_move = self.count_stones_reachable_in_two(board, opponent, rows, cols, score_cols)
        score += player_two_move * 100
        score -= opponent_two_move * 100

        # === POSITIONAL FACTORS (Medium Weight) ===

        # 4. Positional advancement (stones closer to opponent scoring area)
        player_advancement = self.evaluate_positional_advancement(board, player, rows, cols, score_cols)
        opponent_advancement = self.evaluate_positional_advancement(board, opponent, rows, cols, score_cols)
        score += player_advancement * 5
        score -= opponent_advancement * 5

        # 5. Control of central regions and key corridors
        player_control = self.evaluate_board_control(board, player, rows, cols, score_cols)
        opponent_control = self.evaluate_board_control(board, opponent, rows, cols, score_cols)
        score += player_control * 20
        score -= opponent_control * 20

        # 6. Defensive positioning (blocking opponent advancement)
        player_defense = self.evaluate_defensive_positioning(board, player, rows, cols, score_cols)
        opponent_defense = self.evaluate_defensive_positioning(board, opponent, rows, cols, score_cols)
        score += player_defense * 30
        score -= opponent_defense * 30

        # === TACTICAL FACTORS (Lower Weight) ===

        # 7. River network connectivity and flow potential
        player_river_value = self.evaluate_river_network(board, player, rows, cols, score_cols)
        opponent_river_value = self.evaluate_river_network(board, opponent, rows, cols, score_cols)
        score += player_river_value * 15
        score -= opponent_river_value * 15

        # 8. Piece mobility (number of available moves)
        player_mobility = self.count_total_mobility(board, player, rows, cols, score_cols)
        opponent_mobility = self.count_total_mobility(board, opponent, rows, cols, score_cols)
        score += player_mobility * 2
        score -= opponent_mobility * 2

        # 9. Push opportunities (can push opponent pieces away from scoring)
        player_push_ops = self.count_push_opportunities(board, player, rows, cols, score_cols)
        opponent_push_ops = self.count_push_opportunities(board, opponent, rows, cols, score_cols)
        score += player_push_ops * 25
        score -= opponent_push_ops * 25

        return score


"""
Enhanced GreedyAgent Implementation for River and Stones Game

This is a strong bot implementation that replaces the existing GreedyAgent class.
Key improvements:
1. Faster minimax with better pruning
2. Improved evaluation function with more strategic factors
3. Dynamic depth adjustment based on time remaining
4. Better move ordering for alpha-beta pruning
5. Endgame recognition and specialized strategies
"""

import random
import copy
from typing import List, Dict, Any, Optional, Tuple
import time


class EnhancedGreedyAgent(BaseAgent):
    """
    Enhanced Greedy Agent with advanced minimax, strategic evaluation,
    and time management for the River and Stones game.
    """

    def __init__(self, player: str):
        super().__init__(player)
        self.moves_played = 0
        self.time_per_move = 0.0
        self.opponent_pieces_in_scoring = 0
        self.our_pieces_in_scoring = 0

    def choose(self, board: List[List[Any]], rows: int, cols: int, score_cols: List[int],
               current_player_time: float, opponent_time: float, weights: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """
        Enhanced move selection with time-aware depth adjustment and strategic planning.
        """
        self.moves_played += 1

        # Update time management
        self.time_per_move = current_player_time / max(50 - self.moves_played, 10)

        # Get all possible moves
        moves = self.generate_all_moves(board, self.player, rows, cols, score_cols)
        if not moves:
            return None

        # Quick win check - if we can win in one move, do it
        for move in moves:
            ok, new_board = self.simulate_move(board, move, self.player, rows, cols, score_cols)
            if ok:
                winner = self.check_immediate_win(new_board, rows, cols, score_cols)
                if winner == self.player:
                    return move

        # Emergency defense - block opponent from winning
        opponent_moves = self.generate_all_moves(board, self.opponent, rows, cols, score_cols)
        critical_defense = None
        for opp_move in opponent_moves:
            ok, opp_board = self.simulate_move(board, opp_move, self.opponent, rows, cols, score_cols)
            if ok:
                winner = self.check_immediate_win(opp_board, rows, cols, score_cols)
                if winner == self.opponent:
                    # Find a move that blocks this threat
                    critical_defense = self.find_blocking_move(board, moves, opp_move, rows, cols, score_cols)
                    break

        if critical_defense:
            return critical_defense

        # Dynamic depth based on game phase and time
        depth = self.calculate_optimal_depth(board, current_player_time, rows, cols, score_cols)

        start_time = time.time()

        # Use iterative deepening for better time management
        best_move = None
        try:
            for d in range(1, depth + 1):
                if time.time() - start_time > self.time_per_move * 0.8:
                    break

                _, current_best = self.minimax_with_improvements(
                    board, d, float("-inf"), float("inf"), True,
                    self.player, rows, cols, score_cols, weights, start_time
                )

                if current_best:
                    best_move = current_best

        except TimeoutError:
            pass

        return best_move if best_move else random.choice(moves)

    def calculate_optimal_depth(self, board: List[List[Any]], time_remaining: float,
                                rows: int, cols: int, score_cols: List[int]) -> int:
        """Calculate optimal search depth based on game state and time."""
        base_depth = 1

        # Reduce depth in complex positions (many pieces on board)
        piece_count = sum(1 for row in board for cell in row if cell is not None)
        if piece_count > 20:
            base_depth = max(2, base_depth - 1)

        # Increase depth in endgame
        our_scoring = self.count_stones_in_scoring_area(board, self.player, rows, cols, score_cols)
        opp_scoring = self.count_stones_in_scoring_area(board, self.opponent, rows, cols, score_cols)

        if our_scoring >= 2 or opp_scoring >= 2:
            base_depth += 1

        return min(base_depth, 6)  # Cap at depth 6 for performance

    def minimax_with_improvements(self, board: List[List[Any]], depth: int, alpha: float, beta: float,
                                  maximizing: bool, player: str, rows: int, cols: int, score_cols: List[int],
                                  weights: Dict[str, float], start_time: float) -> Tuple[
        float, Optional[Dict[str, Any]]]:
        """
        Enhanced minimax with better pruning, move ordering, and time management.
        """
        # Time cutoff
        if time.time() - start_time > self.time_per_move * 0.9:
            raise TimeoutError()

        if depth == 0:
            return self.enhanced_evaluate_board(board, player, rows, cols, score_cols, weights), None

        # Check for immediate wins/losses
        winner = self.check_immediate_win(board, rows, cols, score_cols)
        if winner == player:
            return 10000 + depth, None  # Prefer faster wins
        elif winner == self.opponent:
            return -10000 - depth, None  # Avoid slower losses

        current_player = player if maximizing else self.opponent
        moves = self.generate_all_moves(board, current_player, rows, cols, score_cols)

        if not moves:
            return self.enhanced_evaluate_board(board, player, rows, cols, score_cols, weights), None

        # Move ordering for better alpha-beta pruning
        moves = self.order_moves(moves, board, current_player, rows, cols, score_cols)

        best_move = None

        if maximizing:
            max_eval = float("-inf")
            for move in moves:
                ok, new_board = self.simulate_move(board, move, current_player, rows, cols, score_cols)
                if not ok:
                    continue

                eval_score, _ = self.minimax_with_improvements(
                    new_board, depth - 1, alpha, beta, False, player, rows, cols, score_cols, weights, start_time
                )

                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move

                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break  # Alpha-beta pruning

            return max_eval, best_move
        else:
            min_eval = float("inf")
            for move in moves:
                ok, new_board = self.simulate_move(board, move, current_player, rows, cols, score_cols)
                if not ok:
                    continue

                eval_score, _ = self.minimax_with_improvements(
                    new_board, depth - 1, alpha, beta, True, player, rows, cols, score_cols, weights, start_time
                )

                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move

                beta = min(beta, eval_score)
                if beta <= alpha:
                    break  # Alpha-beta pruning

            return min_eval, best_move

    def order_moves(self, moves: List[Dict[str, Any]], board: List[List[Any]], player: str,
                    rows: int, cols: int, score_cols: List[int]) -> List[Dict[str, Any]]:
        """
        Order moves to improve alpha-beta pruning efficiency.
        Priority: scoring moves > attacking moves > defensive moves > others
        """

        def move_priority(move):
            priority = 0

            # Highest priority: moves that put stones in scoring area
            if move.get("action") in ["move", "push"]:
                to_pos = move.get("to") or move.get("pushed_to")
                if to_pos and self.is_own_score_cell(to_pos[0], to_pos[1], player, rows, cols, score_cols):
                    priority += 1000

            # High priority: moves that threaten scoring
            if move.get("action") in ["move", "push"]:
                to_pos = move.get("to") or move.get("pushed_to")
                if to_pos:
                    # Check if this move threatens to score next turn
                    if self.threatens_scoring(to_pos, player, rows, cols, score_cols):
                        priority += 500

            # Medium priority: defensive moves (blocking opponent)
            if move.get("action") == "push":
                target_pos = move.get("to")
                if target_pos:
                    piece = board[target_pos[1]][target_pos[0]]
                    if piece and piece.owner != player:
                        priority += 200

            # Lower priority for flip/rotate moves (usually tactical)
            if move.get("action") in ["flip", "rotate"]:
                priority += 50

            return -priority  # Negative for descending order

        return sorted(moves, key=move_priority)

    def enhanced_evaluate_board(self, board: List[List[Any]], player: str, rows: int, cols: int,
                                score_cols: List[int], weights: Dict[str, float]) -> float:
        """
        Comprehensive board evaluation with multiple strategic factors.
        """
        opponent = self.opponent
        score = 0.0

        # 1. Pieces in scoring areas (most important)
        our_scoring = self.count_stones_in_scoring_area(board, player, rows, cols, score_cols)
        opp_scoring = self.count_stones_in_scoring_area(board, opponent, rows, cols, score_cols)
        score += (our_scoring - opp_scoring) * 2000

        # 2. Pieces that can reach scoring in one move
        our_reachable = self.count_reachable_in_one_move(board, player, rows, cols, score_cols)
        opp_reachable = self.count_reachable_in_one_move(board, opponent, rows, cols, score_cols)
        score += (our_reachable - opp_reachable) * 800

        # 3. Pieces that can reach scoring in two moves
        our_two_move = self.count_reachable_in_two_moves(board, player, rows, cols, score_cols)
        opp_two_move = self.count_reachable_in_two_moves(board, opponent, rows, cols, score_cols)
        score += (our_two_move - opp_two_move) * 200

        # 4. Control of scoring columns
        our_column_control = self.evaluate_column_control(board, player, rows, cols, score_cols)
        opp_column_control = self.evaluate_column_control(board, opponent, rows, cols, score_cols)
        score += (our_column_control - opp_column_control) * 150

        # 5. River network value
        our_river_value = self.evaluate_river_network(board, player, rows, cols, score_cols)
        opp_river_value = self.evaluate_river_network(board, opponent, rows, cols, score_cols)
        score += (our_river_value - opp_river_value) * 100

        # 6. Positional advancement
        our_advancement = self.evaluate_positional_advancement(board, player, rows, cols, score_cols)
        opp_advancement = self.evaluate_positional_advancement(board, opponent, rows, cols, score_cols)
        score += (our_advancement - opp_advancement) * 80

        # 7. Defensive positioning
        our_defense = self.evaluate_defensive_positioning(board, player, rows, cols, score_cols)
        opp_defense = self.evaluate_defensive_positioning(board, opponent, rows, cols, score_cols)
        score += (our_defense - opp_defense) * 120

        # 8. Piece mobility
        our_mobility = self.count_total_moves(board, player, rows, cols, score_cols)
        opp_mobility = self.count_total_moves(board, opponent, rows, cols, score_cols)
        score += (our_mobility - opp_mobility) * 10

        # 9. Push opportunities
        our_pushes = self.count_push_opportunities(board, player, rows, cols, score_cols)
        opp_pushes = self.count_push_opportunities(board, opponent, rows, cols, score_cols)
        score += (our_pushes - opp_pushes) * 60

        return score

    def count_reachable_in_one_move(self, board: List[List[Any]], player: str,
                                    rows: int, cols: int, score_cols: List[int]) -> int:
        """Count stones that can reach scoring area in one move."""
        count = 0
        target_row = top_score_row() if player == "circle" else bottom_score_row(rows)

        for y in range(rows):
            for x in range(cols):
                piece = board[y][x]
                if not piece or piece.owner != player or piece.side != "stone":
                    continue

                if y == target_row and x in score_cols:
                    continue  # Already in scoring area

                # Check if can reach scoring area via moves or pushes
                info = agent_compute_valid_moves(board, x, y, player, rows, cols, score_cols)

                for tx, ty in info['moves']:
                    if ty == target_row and tx in score_cols:
                        count += 1
                        break

                for (_, (px, py)) in info['pushes']:
                    if py == target_row and px in score_cols:
                        count += 1
                        break

        return count

    def count_reachable_in_two_moves(self, board: List[List[Any]], player: str,
                                     rows: int, cols: int, score_cols: List[int]) -> int:
        """Count stones that can reach scoring area in two moves."""
        count = 0
        target_row = top_score_row() if player == "circle" else bottom_score_row(rows)

        for y in range(rows):
            for x in range(cols):
                piece = board[y][x]
                if not piece or piece.owner != player or piece.side != "stone":
                    continue

                if y == target_row and x in score_cols:
                    continue  # Already in scoring

                if self.can_reach_in_moves(board, x, y, player, target_row, score_cols, rows, cols, 1):
                    continue  # Already counted in one-move

                if self.can_reach_in_moves(board, x, y, player, target_row, score_cols, rows, cols, 2):
                    count += 1

        return count

    def can_reach_in_moves(self, board: List[List[Any]], start_x: int, start_y: int, player: str,
                           target_row: int, score_cols: List[int], rows: int, cols: int, max_moves: int) -> bool:
        """Check if piece can reach scoring area within max_moves."""
        if max_moves <= 0:
            return False

        # Simple BFS simulation
        queue = [(start_x, start_y, 0)]
        visited = set()

        while queue:
            x, y, moves = queue.pop(0)

            if moves > max_moves:
                continue

            if (x, y, moves) in visited:
                continue
            visited.add((x, y, moves))

            if y == target_row and x in score_cols:
                return True

            if moves < max_moves:
                # Add adjacent positions
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if in_bounds(nx, ny, rows, cols):
                        queue.append((nx, ny, moves + 1))

        return False

    def evaluate_column_control(self, board: List[List[Any]], player: str,
                                rows: int, cols: int, score_cols: List[int]) -> float:
        """Evaluate control of scoring columns."""
        control = 0.0

        for col in score_cols:
            player_pieces = 0
            opponent_pieces = 0

            for row in range(rows):
                piece = board[row][col]
                if piece:
                    if piece.owner == player:
                        player_pieces += 1
                    else:
                        opponent_pieces += 1

            # Bonus for controlling columns
            if player_pieces > opponent_pieces:
                control += (player_pieces - opponent_pieces) * 10

        return control

    def evaluate_river_network(self, board: List[List[Any]], player: str,
                               rows: int, cols: int, score_cols: List[int]) -> float:
        """Evaluate the strategic value of river networks."""
        river_value = 0.0

        for y in range(rows):
            for x in range(cols):
                piece = board[y][x]
                if piece and piece.owner == player and piece.side == "river":
                    river_value += 20  # Base river value

                    # Bonus if river is in scoring column
                    if x in score_cols:
                        river_value += 30

                    # Bonus for rivers that create long paths
                    flow_destinations = agent_river_flow(board, x, y, x, y, player, rows, cols, score_cols)
                    river_value += len(flow_destinations) * 3

        return river_value

    def evaluate_positional_advancement(self, board: List[List[Any]], player: str,
                                        rows: int, cols: int, score_cols: List[int]) -> float:
        """Evaluate how advanced pieces are toward opponent's scoring area."""
        advancement = 0.0
        target_row = bottom_score_row(rows) if player == "circle" else top_score_row()

        for y in range(rows):
            for x in range(cols):
                piece = board[y][x]
                if piece and piece.owner == player and piece.side == "stone":
                    distance_to_target = abs(y - target_row)
                    advancement += max(0, 10 - distance_to_target)

                    # Extra bonus if in scoring column
                    if x in score_cols:
                        advancement += max(0, 15 - distance_to_target)

        return advancement

    def evaluate_defensive_positioning(self, board: List[List[Any]], player: str,
                                       rows: int, cols: int, score_cols: List[int]) -> float:
        """Evaluate defensive positioning near our scoring area."""
        defense = 0.0
        our_score_row = top_score_row() if player == "circle" else bottom_score_row(rows)

        # Check area around our scoring row
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                for col in score_cols:
                    x, y = col + dx, our_score_row + dy
                    if in_bounds(x, y, rows, cols):
                        piece = board[y][x]
                        if piece and piece.owner == player:
                            distance = abs(dx) + abs(dy)
                            defense += max(0, 5 - distance)

        return defense

    def count_total_moves(self, board: List[List[Any]], player: str,
                          rows: int, cols: int, score_cols: List[int]) -> int:
        """Count total available moves for mobility evaluation."""
        return len(self.generate_all_moves(board, player, rows, cols, score_cols))

    def count_push_opportunities(self, board: List[List[Any]], player: str,
                                 rows: int, cols: int, score_cols: List[int]) -> int:
        """Count opportunities to push opponent pieces."""
        push_count = 0
        moves = self.generate_all_moves(board, player, rows, cols, score_cols)

        for move in moves:
            if move.get("action") == "push":
                target_pos = move.get("to")
                if target_pos:
                    piece = board[target_pos[1]][target_pos[0]]
                    if piece and piece.owner != player:
                        push_count += 1

        return push_count

    def threatens_scoring(self, pos: Tuple[int, int], player: str,
                          rows: int, cols: int, score_cols: List[int]) -> bool:
        """Check if a position threatens to score next turn."""
        x, y = pos
        target_row = bottom_score_row(rows) if player == "circle" else top_score_row()

        # Check if adjacent to scoring area
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if ny == target_row and nx in score_cols:
                return True

        return False

    def check_immediate_win(self, board: List[List[Any]], rows: int, cols: int, score_cols: List[int]) -> Optional[str]:
        """Check if either player has won."""
        circle_count = self.count_stones_in_scoring_area(board, "circle", rows, cols, score_cols)
        square_count = self.count_stones_in_scoring_area(board, "square", rows, cols, score_cols)

        if circle_count >= 4:
            return "circle"
        elif square_count >= 4:
            return "square"
        return None

    def find_blocking_move(self, board: List[List[Any]], moves: List[Dict[str, Any]],
                           threat_move: Dict[str, Any], rows: int, cols: int, score_cols: List[int]) -> Optional[
        Dict[str, Any]]:
        """Find a move that blocks an opponent's winning threat."""
        # This is a simplified implementation - can be enhanced
        for move in moves:
            if move.get("action") == "push":
                # Try to push opponent pieces away from scoring
                return move
        return None

    # Include all the utility methods from the original GreedyAgent
    def count_stones_in_scoring_area(self, board: List[List[Any]], player: str, rows: int, cols: int,
                                     score_cols: List[int]) -> int:
        """Count stones in player's scoring area."""
        count = 0
        if player == "circle":
            score_row = top_score_row()
        else:
            score_row = bottom_score_row(rows)

        for x in score_cols:
            if 0 <= x < cols and 0 <= score_row < rows:
                piece = board[score_row][x]
                if piece and piece.owner == player and piece.side == "stone":
                    count += 1
        return count

    def is_own_score_cell(self, x: int, y: int, player: str, rows: int, cols: int, score_cols: List[int]) -> bool:
        """Check if cell is in player's own scoring area."""
        if player == "circle":
            return (y == top_score_row()) and (x in score_cols)
        else:
            return (y == bottom_score_row(rows)) and (x in score_cols)


def get_agent(player: str, strategy: str) -> BaseAgent:
    """Factory for creating agents by name"""
    strategy = strategy.lower()
    if strategy == "random":
        return EnhancedGreedyAgent(player)
    elif strategy == "greedy":
        return GreedyAgent(player)
    elif strategy == "student":
        return StudentAgent(player)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
