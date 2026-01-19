import os
import shutil


def remove_pycache_folders(root_dir):
    for root, dirs, files in os.walk(root_dir):
        for dir_name in dirs:
            if dir_name == "__pycache__":
                pycache_dir = os.path.join(root, dir_name)
                shutil.rmtree(pycache_dir)
                print(f"Removed {pycache_dir}")


# 调用函数，并指定需要删除 __pycache__ 文件夹的项目目录
remove_pycache_folders(".")
