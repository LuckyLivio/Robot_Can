const DEMO_DATA = {
  "cases": [
    {
      "id": "clean_shared_success",
      "label": "三种方法均成功",
      "condition": "clean",
      "state_name": "demo_1000001",
      "eligible_count": 51,
      "video": "../../release_20261012_01/demo/videos/clean_shared_success.mp4",
      "poster": "../../release_20261012_01/demo/posters/clean_shared_success.png",
      "frames": 59,
      "fps": 10,
      "duration_s": 5.9,
      "control_steps": 95,
      "sha256": "0f82a9ecc63910e596a3a093eed4f821ab9d9734b8d661d905cca172467d22ef",
      "elapsed_render_s": 5.050939599999765,
      "results": {
        "bc_k2": {
          "success": true,
          "steps": 95
        },
        "full": {
          "success": true,
          "steps": 95
        },
        "plain": {
          "success": true,
          "steps": 95
        }
      },
      "firstFrame": "../../review_20261012_01/demo/posters/clean_shared_success_first.jpg"
    },
    {
      "id": "clean_full_only_success",
      "label": "Full成功，BC与Plain未完成",
      "condition": "clean",
      "state_name": "demo_1000026",
      "eligible_count": 1,
      "video": "../../release_20261012_01/demo/videos/clean_full_only_success.mp4",
      "poster": "../../release_20261012_01/demo/posters/clean_full_only_success.png",
      "frames": 211,
      "fps": 10,
      "duration_s": 21.1,
      "control_steps": 400,
      "sha256": "6eb234be82340b437909d29dcc95e2e64d0cc00b79cefd5d09eb44d7e5e0ffd4",
      "elapsed_render_s": 11.46932469999956,
      "results": {
        "bc_k2": {
          "success": false,
          "steps": 400
        },
        "full": {
          "success": true,
          "steps": 133
        },
        "plain": {
          "success": false,
          "steps": 400
        }
      },
      "firstFrame": "../../review_20261012_01/demo/posters/clean_full_only_success_first.jpg"
    },
    {
      "id": "clean_shared_failure",
      "label": "三种方法均未完成",
      "condition": "clean",
      "state_name": "demo_1000000",
      "eligible_count": 6,
      "video": "../../release_20261012_01/demo/videos/clean_shared_failure.mp4",
      "poster": "../../release_20261012_01/demo/posters/clean_shared_failure.png",
      "frames": 211,
      "fps": 10,
      "duration_s": 21.1,
      "control_steps": 400,
      "sha256": "7e717c4137045b7c5368513bff5e60e711114bc35a6149a80af36c7322604f7b",
      "elapsed_render_s": 15.51588399999855,
      "results": {
        "bc_k2": {
          "success": false,
          "steps": 400
        },
        "full": {
          "success": false,
          "steps": 400
        },
        "plain": {
          "success": false,
          "steps": 400
        }
      },
      "firstFrame": "../../review_20261012_01/demo/posters/clean_shared_failure_first.jpg"
    },
    {
      "id": "noise005_shared_success",
      "label": "三种方法均成功",
      "condition": "noise005",
      "state_name": "demo_1000002",
      "eligible_count": 49,
      "video": "../../release_20261012_01/demo/videos/noise005_shared_success.mp4",
      "poster": "../../release_20261012_01/demo/posters/noise005_shared_success.png",
      "frames": 66,
      "fps": 10,
      "duration_s": 6.6,
      "control_steps": 110,
      "sha256": "2380d532f9d96f247132284f0a9af902bbe976558b132970013de5775d2d7fc6",
      "elapsed_render_s": 5.208734899999399,
      "results": {
        "bc_k2": {
          "success": true,
          "steps": 110
        },
        "full": {
          "success": true,
          "steps": 109
        },
        "plain": {
          "success": true,
          "steps": 110
        }
      },
      "firstFrame": "../../review_20261012_01/demo/posters/noise005_shared_success_first.jpg"
    },
    {
      "id": "noise005_full_only_success",
      "label": "Full成功，BC与Plain未完成",
      "condition": "noise005",
      "state_name": "demo_1000011",
      "eligible_count": 2,
      "video": "../../release_20261012_01/demo/videos/noise005_full_only_success.mp4",
      "poster": "../../release_20261012_01/demo/posters/noise005_full_only_success.png",
      "frames": 211,
      "fps": 10,
      "duration_s": 21.1,
      "control_steps": 400,
      "sha256": "f57cfe274160c2709f07a0ae808891bda0e55c8e5ce62d91a5acad2c510302d3",
      "elapsed_render_s": 11.62310830000024,
      "results": {
        "bc_k2": {
          "success": false,
          "steps": 400
        },
        "full": {
          "success": true,
          "steps": 165
        },
        "plain": {
          "success": false,
          "steps": 400
        }
      },
      "firstFrame": "../../review_20261012_01/demo/posters/noise005_full_only_success_first.jpg"
    },
    {
      "id": "noise005_shared_failure",
      "label": "三种方法均未完成",
      "condition": "noise005",
      "state_name": "demo_1000000",
      "eligible_count": 8,
      "video": "../../release_20261012_01/demo/videos/noise005_shared_failure.mp4",
      "poster": "../../release_20261012_01/demo/posters/noise005_shared_failure.png",
      "frames": 211,
      "fps": 10,
      "duration_s": 21.1,
      "control_steps": 400,
      "sha256": "b9b3ba9a141e2008c7e8716f62ea8dd579728cb655ddade19a5fc8495925d64f",
      "elapsed_render_s": 14.208406299998387,
      "results": {
        "bc_k2": {
          "success": false,
          "steps": 400
        },
        "full": {
          "success": false,
          "steps": 400
        },
        "plain": {
          "success": false,
          "steps": 400
        }
      },
      "firstFrame": "../../review_20261012_01/demo/posters/noise005_shared_failure_first.jpg"
    }
  ],
  "statistics": [
    {
      "method": "bc_k2",
      "condition": "clean",
      "rate": 85.0,
      "counts": [
        51
      ]
    },
    {
      "method": "full",
      "condition": "clean",
      "rate": 90.0,
      "counts": [
        54,
        54,
        54
      ]
    },
    {
      "method": "plain",
      "condition": "clean",
      "rate": 88.33333333333333,
      "counts": [
        53,
        53,
        53
      ]
    },
    {
      "method": "bc_k2",
      "condition": "noise005",
      "rate": 81.66666666666667,
      "counts": [
        49
      ]
    },
    {
      "method": "full",
      "condition": "noise005",
      "rate": 86.11111111111111,
      "counts": [
        52,
        52,
        51
      ]
    },
    {
      "method": "plain",
      "condition": "noise005",
      "rate": 83.88888888888889,
      "counts": [
        50,
        51,
        50
      ]
    }
  ]
};
