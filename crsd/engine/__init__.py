"""Engine CRSD: cấu hình game, vòng chơi, tính điểm, dựng prompt.

Cố ý KHÔNG import sẵn các submodule nặng (vd model factory) để phần logic
thuần (scoring, parse) test được mà không cần torch/vllm.
"""
