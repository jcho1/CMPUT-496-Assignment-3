"""
Module for playing games of Go using GoTextProtocol

This code is based off of the gtp module in the Deep-Go project
by Isaac Henrion and Aamos Storkey at the University of Edinburgh.
"""
import traceback
import sys
import os
from board_util import GoBoardUtil, BLACK, WHITE, EMPTY, BORDER, FLOODFILL
import gtp_connection
import numpy as np
import re

class GtpConnection2(gtp_connection.GtpConnection):

    def __init__(self, go_engine, board, outfile = 'gtp_log', debug_mode = False):
        """
        object that plays Go using GTP

        Parameters
        ----------
        go_engine : GoPlayer
            a program that is capable of playing go by reading GTP commands
        komi : float
            komi used for the current game
        board: GoBoard
            SIZExSIZE array representing the current board state
        """
        gtp_connection.GtpConnection.__init__(self, go_engine, board, outfile, debug_mode)
        self.commands["policy_moves"] = self.policy_moves_cmd


    def policy_moves_cmd(self, args):
        """
        Return list of policy moves for the current_player of the board
        """
        policy_moves, type_of_move = self.generate_all_policy_moves(self.board,
                                                        self.go_engine.use_pattern,
                                                        self.go_engine.check_selfatari)
        if len(policy_moves) == 0:
            self.respond("Pass")
        else:
            response = type_of_move + " " + GoBoardUtil.sorted_point_string(policy_moves, self.board.NS)
            self.respond(response)

    def generate_all_policy_moves(self, board,pattern,check_selfatari):
        """
            generate a list of policy moves on board for board.current_player.
            Use in UI only. For playing, use generate_move_with_filter
            which is more efficient
        """
        if pattern:

            atari_moves,msg = self.generate_atari_moves(board)
            atari_moves = GoBoardUtil.filter_moves(board, atari_moves, check_selfatari)
            if len(atari_moves) > 0:
                return atari_moves, msg

            pattern_moves = []
            pattern_moves = GoBoardUtil.generate_pattern_moves(board)
            pattern_moves = GoBoardUtil.filter_moves(board, pattern_moves, check_selfatari)
            if len(pattern_moves) > 0:
                return pattern_moves, "Pattern"
        return GoBoardUtil.generate_random_moves(board,True), "Random"

    def generate_atari_moves(self, board):
        color = board.current_player
        opp_color = GoBoardUtil.opponent(color)
        if not board.last_move:
            return [],"None"
        last_lib_point = board._single_liberty(board.last_move, opp_color)
        if last_lib_point: #When num of liberty is 1 for last point we will get this point
            if board.check_legal(last_lib_point,color):
                return [last_lib_point],"AtariCapture"
        moves = self.atari_defence(board, board.last_move, color)
        return moves,"AtariDefense"


    def atari_defence(self, board, point, color):
        moves = []
        for n in board._neighbors(point):
            if board.board[n] == color:
                last_lib_point = board._single_liberty(n, color)
                if last_lib_point:
                    defend_move = self.runaway(board, last_lib_point, color)
                    if defend_move:
                        moves.append(defend_move)
                    attack_moves = self.counterattack(board, n)
                    if attack_moves:
                        moves = moves + attack_moves
        return moves

    def runaway(self, board, point, color):
        cboard = board.copy()
        if cboard.move(point, color):
            if cboard._liberty(point,color) > 1:
                return point
            else:
                return None

    def counterattack(self, board, point):
        color = board.board[point]
        opp_color = GoBoardUtil.opponent(color)
        moves = []
        for n in board._neighbors(point):
            if board.board[n] == opp_color:
                opp_single_lib = board._single_liberty(n, opp_color)
                if opp_single_lib:
                    cboard = board.copy()
                    if cboard.move(opp_single_lib, color):
                        if cboard._liberty(point, color) > 1:
                            moves.append(opp_single_lib)
        return moves

