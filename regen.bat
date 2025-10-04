@echo off
cd /d %~dp0
python generate_kifu_list.py && python generate_index_with_search.py
