"""crsd — Collective-Risk Social Dilemma cho LLM agents.

Mô phỏng trò chơi của Milinski et al. (2008, PNAS) — "The collective-risk
social dilemma and the prevention of simulated dangerous climate change" —
nhưng người chơi là các mô hình ngôn ngữ lớn (LLM) thay vì con người.

Kiến trúc mô phỏng FairGame (config-driven, đa ngôn ngữ, hỗ trợ chạy offline),
tái dùng các connector trong package ``FAIRGAME`` (gồm local_vllm_connector của
dự án) cho phần gọi mô hình. Cơ chế tính điểm là threshold + xổ số rủi ro
(không dùng payoff matrix như các game 2 người của FairGame).

Xem ``docs/design/architecture.md`` để hiểu tổng thể.
"""

__version__ = "0.1.0"
