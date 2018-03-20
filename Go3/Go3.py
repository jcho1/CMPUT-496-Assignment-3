#!/usr/bin/python3
import os, sys
utilpath = sys.path[0] + "/../util/"
sys.path.append(utilpath)

from gtp_connection2 import GtpConnection2
from board_util import GoBoardUtil
from simple_board import SimpleGoBoard
from ucb import runUcb
import numpy as np
import argparse
import sys
import copy

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--sim', type=int, default=10, help='number of simulations per move, so total playouts=sim*legal_moves')
parser.add_argument('--moveselect', type=str, default='simple', help='type of move selection: simple or ucb')
parser.add_argument('--simulations', type=str, default='random', help='type of simulation policy: random or rulebased')
parser.add_argument('--movefilter', action='store_true', default=False, help='whether use move filter or not')

args = parser.parse_args()
num_simulation = args.sim
move_select = args.moveselect
simulations = args.simulations
move_filter = args.movefilter

# pair = (move, percentage)
def byPercentage(pair):
    return pair[1]

def writeMoves(board, moves, count, numSimulations):
    gtp_moves = []
    for i in range(len(moves)):
        if moves[i] != None:
            x, y = board._point_to_coord(moves[i])
            gtp_moves.append((GoBoardUtil.format_point((x, y)),
                          float(count[i])/float(numSimulations)))
        else:
            gtp_moves.append(('Pass',float(count[i])/float(numSimulations)))
    sys.stderr.write("win rates: {}\n"
                     .format(sorted(gtp_moves, key = byPercentage,
                                               reverse = True)))
    sys.stderr.flush()

def select_best_move(board, moves, moveWins):
    max_child = np.argmax(moveWins)
    return moves[max_child]


class Go3Player(object):
    """
    Flat Monte Carlo implementation that uses simulation for finding the best child of a given node
    """

    version = 0.22
    name = "Go3"
    def __init__(self,num_simulation,size=7,limit=100):
        self.num_simulation = num_simulation
        self.limit = limit
        self.use_ucb = False if move_select =='simple' else True
        self.random_simulation = True if simulations == 'random' else False
        self.use_pattern = not self.random_simulation
        self.check_selfatari = move_filter

    def simulate(self, board, cboard, move, toplay):
        GoBoardUtil.copyb2b(board,cboard)
        assert cboard.board.all() == board.board.all()
        cboard.move(move, toplay)
        opp = GoBoardUtil.opponent(toplay)
        return GoBoardUtil.playGame(cboard,
                opp,
                komi=self.komi,
                limit=self.limit,
                random_simulation = self.random_simulation,
                use_pattern = self.use_pattern,
                check_selfatari= self.check_selfatari)

    def simulateMove(self, board, cboard, move, toplay):
        wins = 0
        for _ in range(self.num_simulation):
            result = self.simulate(board, cboard, move, toplay)
            if result == toplay:
                wins += 1
        return wins
    
    def get_move(self, board, toplay):
        cboard = board.copy()
        emptyPoints = board.get_empty_points()
        moves = []

        if simulations == "rulebased":
            for p in self.generate_all_policy_moves(board, self.use_pattern,
                                                    self.check_selfatari,
                                                              toplay):
                moves.append(p)
        else:
            for p in emptyPoints:
                if board.check_legal(p, toplay):
                    moves.append(p)

        if not moves: # pass move only, no need to simulate
            return None
        moves.append(None) # None for Pass
        if self.use_ucb == True:
            C = 0.4 #sqrt(2) is safe, this is more aggressive
            best = runUcb(self, board, cboard, C, moves, toplay)
            return best
        else:
            moveWins = []
            for move in moves:
                wins = self.simulateMove(board, cboard, move, toplay)
                moveWins.append(wins)
            writeMoves(board, moves, moveWins, self.num_simulation)
            return select_best_move(board, moves, moveWins)

    def get_properties(self):
        return dict(
            version=self.version,
            name=self.__class__.__name__,
        )

 
    def generate_all_policy_moves(self, board,pattern,check_selfatari, color):
        if pattern:

            atari_moves,msg = self.generate_atari_moves(board, color)
            atari_moves = GoBoardUtil.filter_moves(board, atari_moves, check_selfatari)
            if len(atari_moves) > 0:
                return atari_moves

            pattern_moves = []
            pattern_moves = GoBoardUtil.generate_pattern_moves(board)
            pattern_moves = GoBoardUtil.filter_moves(board, pattern_moves, check_selfatari)
            if len(pattern_moves) > 0:
                return pattern_moves

        return GoBoardUtil.generate_random_moves(board,True)

    def generate_atari_moves(self, board, color):
        opponent = GoBoardUtil.opponent(color)
        if not board.last_move:
            return [],""

        last_liberty = board._single_liberty(board.last_move, opponent)
        if last_liberty and board.check_legal(last_liberty,color):
                return [last_liberty],"AtariCapture"

        moves = self.atari_defence(board, board.last_move, color)
        return moves,"AtariDefense"


    def atari_defence(self, board, point, color):
        moves = []
        for n in board._neighbors(point):
            if board.board[n] == color:
                last_liberty = board._single_liberty(n, color)
                if last_liberty:
                    defend_move = self.runaway(board, last_liberty, color)
                    if defend_move:
                        moves.append(defend_move)
                    attack_moves = self.capture(board, n, color)
                    if attack_moves:
                        moves = moves + attack_moves
        return moves

    def runaway(self, board, point, color):
        copy_board = board.copy()
        if copy_board.move(point, color) and copy_board._liberty(point,color) > 1:
            return point

    def capture(self, board, point, color):
        opponent = GoBoardUtil.opponent(color)
        copy_board = board.copy()
        moves = []
        for n in board._neighbors(point):
            if board.board[n] == opponent:
                opponent_liberty = board._single_liberty(n, opponent)
                if opponent_liberty:
                    if copy_board.move(opponent_liberty, color):
                        if copy_board._liberty(point, color) > 1:
                            moves.append(opponent_liberty)
        return moves




def run():
    """
    start the gtp connection and wait for commands.
    """
    board = SimpleGoBoard(7)
    con = GtpConnection2(Go3Player(num_simulation), board)
    con.start_connection()

if __name__=='__main__':
    if move_select != "simple" and move_select != "ucb":
        print('moveselect must be simple or ucb')
        sys.exit(0)
    if simulations != "random" and simulations != "rulebased":
        print('simulations must be random or rulebased')
        sys.exit(0)
    run()

