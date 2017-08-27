import gzip
import json
import os
from os import path
from stratified_bayesian_optimization.util.json_file import JSONFile
from stratified_bayesian_optimization.initializers.log import SBOLog
import ujson
from bisect import bisect_left

logger = SBOLog(__name__)


class StatisticsProcessedData(object):

    _name_file_ = 'problems/arxiv/data/{year}_{month}_processed_data.json'.format
    _name_file_categories = 'problems/arxiv/data/papers.json'
    _name_file_final = 'problems/arxiv/data/{year}_{month}_top_users.json'.format
    _papers_path = '/data/json/idcat/'

    @classmethod
    def top_users_papers(cls, year, month, n_entries=100, different_papers=20, top_n=5000,
                         n_users=None, only_assign_categories=True):
        """
        Returns the users that accessed to at least n_entries papers, and at least different_papers
        were different and were in the top_n papers in the month of the year.

        Returns the top_n papers based on how many times they were seen.

        :param year: (str)
        :param month: (str) e.g. '1', '12'
        :param n_entries: (int)
        :param different_papers: int
        :param top_n: int
        :param n_users: (int) Maximum number of users allowed
        :return: [ {'paper': (int) number of times seen},
            {'user': {'stats': ((int) # entries, (int) # different papers in the top_n papers),
                      'diff_papers': [str]
                }
            }
        ]
        """

        file_name = cls._name_file_(year=year, month=month)
        data = JSONFile.read(file_name)

        users = data[0]
        papers = data[1]

        n_papers = []
        paper_ls = []
        for paper in papers:
            paper_ls.append(paper)
            n_papers.append(papers[paper]['views'])
        index_top_papers = sorted(range(len(n_papers)), key=lambda k: n_papers[k])
        index_top_papers = index_top_papers[-top_n:]

        rank_papers = {}
        for index in index_top_papers:
            rank_papers[paper_ls[index]] = n_papers[index]

        paper_ls = rank_papers.keys()

        cls.assign_categories(paper_ls)

        if only_assign_categories:
            return

        rank_user = {}

        users_ls = []
        n_entries_ls = []

        for user in users:
            users_ls.append(user)
            n_entries_ls.append(sum(users[user].values()))

        index_top_users = sorted(range(len(n_entries_ls)), key=lambda k: n_entries_ls[k])
        users_ls = [users_ls[i] for i in index_top_users]
        n_entries_ls = [n_entries_ls[i] for i in index_top_users]
        ind_bis = bisect_left(n_entries_ls, n_entries)

        users_ls = users_ls[ind_bis:]
        n_entries_ls = n_entries_ls[ind_bis:]

        final_users = []
        metric_users = []
        for user, n in zip(users_ls, n_entries_ls):
            diff_papers = set(users[user].keys()).intersection(set(paper_ls))
            n_diff = len(diff_papers)
            if n_diff < different_papers:
                continue
            final_users.append(user)
            metric_users.append(n_diff)
            rank_user[user] = {'stats': (n, n_diff), 'diff_papers': diff_papers}

        index_top_users = sorted(range(len(final_users)), key=lambda k: metric_users[k])

        if n_users is not None and len(index_top_users) > n_users:
            index_top_users = index_top_users[-n_users:]

            rank_user_final = {}
            for ind in index_top_users:
                rank_user_final[final_users[ind]] = rank_user[final_users[ind]]
            rank_user = rank_user_final

        file_name = cls._name_file_final(year=year, month=month)
        JSONFile.write([rank_papers, rank_user], file_name)

        logger.info('Number of papers is %d' % len(rank_papers))
        logger.info('Number of users is %d' % len(rank_user))


        return [rank_papers, rank_user]

    @classmethod
    def assign_categories_date_year(cls, year, month):
        """
        :param year: (str)
        :param month: (str) e.g. '1', '12'
        :return:
        """

        file_name = cls._name_file_final(year=year, month=month)
        data = JSONFile.read(file_name)
        papers = data[0].keys()
        cls.assign_categories(papers)

    @classmethod
    def assign_categories(cls, list_papers):
        """

        :param list_papers: [str]
        :return: {paper_name (str):  category (str)}
        """
        papers = {}
        for paper in list_papers:

            before_2007 = False
            arxiv_id = paper

            if '/' in arxiv_id:
                 before_2007 = True
                 index = arxiv_id.index('/')
                 cat = arxiv_id[0: index]
                 arxiv_id = arxiv_id[index + 1:]

            if 'v' in arxiv_id:
                index = arxiv_id.rfind('v')
                arxiv_id = arxiv_id[0: index]

            if not before_2007:
                cat = cls.get_cats(arxiv_id, arxiv_id[0: 2], arxiv_id[2: 4])

            papers[paper] = cat

        JSONFile.write(papers, cls._name_file_categories)
        return papers

    @classmethod
    def get_cats(cls, arxiv_id, year, month):
          """
          Get category of a file

          :param arxiv_id: (str)
          :param year: (str) e.g. '07', '10'
          :param month: (str) e.g. '12', '02'
          :return: str

          """

          filename = path.join(cls._papers_path, '20' + year)
          date = year + month

          cats = None

          for day in xrange(1, 32):
               if day < 10:
                    date_ = date + '0' + str(day)
               else:
                    date_ = date + str(day)

               date_ += '_idcat.json'
               filename_ = path.join(filename, date_)


               data = None
               if path.exists(filename_):
                    with open(filename_) as f:
                         data = ujson.load(f)

               if data is not None:
                    for dicts in data['new']:
                         if dicts['id'] == arxiv_id:
                              cats = [a.lower() for a in dicts["cat"].split(":")]
                              break

               if cats is not None:
                    return cats[0]

          new_month = int(month) + 1

          if new_month == 13:
               new_month = 1
               year = int(year) + 1
               if year < 10:
                    year = '0' + str(year)
               else:
                    year = str(year)

          if new_month < 10:
               new_month = '0' + str(new_month)
          else:
               new_month = str(new_month)

          filename = path.join(cls._papers_path, '20' + year)

          for day in xrange(1, 10):
               date = year + new_month + '0' + str(day) + '_idcat.json'
               filename_ = path.join(filename, date)

               data = None
               if path.exists(filename_):
                    with open(filename_) as f:
                         data = ujson.load(f)

               if data is not None:
                    for dicts in data['new']:
                         if dicts['id'] == arxiv_id:
                              cats = [a.lower() for a in dicts["cat"].split(":")]
                              break

               if cats is not None:
                    return cats[0]

          if cats is None:
               logger.info("Couldn't find category of paper %s" % arxiv_id)

          return cats


    def top_papers_year(self, n, year):
        """
        Returns the top n papers seen in the year
        :param n: int
        :param year: str
        :return: n * [str]
        """
        pass
