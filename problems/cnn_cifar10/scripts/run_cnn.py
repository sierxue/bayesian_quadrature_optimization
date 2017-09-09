from __future__ import absolute_import

from problems.cnn_cifar10.cnn import train_nn

import argparse
from stratified_bayesian_optimization.util.json_file import JSONFile


if __name__ == '__main__':
    # Example usage:
    # python -m problems.cnn_cifar10.scripts.run_cnn 1

    parser = argparse.ArgumentParser()
    parser.add_argument('random_seed', help='e.g. 2')

    args = parser.parse_args()
    rs = int(args.random_seed)

    errors = train_nn(rs)

    directory = 'problems/cnn_cifar10/runs_random_seeds/' + 'rs_%d' % rs

    JSONFile.write(errors, directory)
