#!/usr/bin/python3
import os, sys
utilpath = sys.path[0] + "/../util/"
sys.path.append(utilpath)

from gtp_connection2 import GtpConnection  
from board_util2 import GoBoardUtil
from simple_board import SimpleGoBoard
from ucb import runUcb
import numpy as np
import argparse
import sys
import copy

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--simulations', type=str, default='random', help='type of simulation policy: random or rulebased')
parser.add_argument('--movefilter', action='store_true', default=False, help='whether use move filter or not')

args = parser.parse_args()
simulations = args.simulations
move_filter = args.movefilter

class PolicyPlayer(object):
    """
    Flat Monte Carlo implementation that uses simulation for finding the best child of a given node
    """

    version = 0.22
    name = "PolicyPlayer"
    def __init__(self):
        self.random_simulation = True if simulations == 'random' else False
        self.use_pattern = not self.random_simulation
        self.check_selfatari = move_filter
    
    def get_move(self, board, toplay):
        return GoBoardUtil.generate_move_with_filter(board, self.use_pattern, self.check_selfatari)

    def get_properties(self):
        return dict(
            version=self.version,
            name=self.__class__.__name__,
        )

def run():
    """
    start the gtp connection and wait for commands.
    """
    board = SimpleGoBoard(7)
    con = GtpConnection(PolicyPlayer(), board)
    con.start_connection()

if __name__=='__main__':
    run()

