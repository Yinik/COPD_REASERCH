# 用之前给你的BioPython代码，搜中文糖尿病文献
from Bio import Entrez
Entrez.email = "你的邮箱@qq.com"
handle = Entrez.esearch(db="pubmed", term="diabetes[Title/Abstract] AND chinese[Language]", retmax=50)