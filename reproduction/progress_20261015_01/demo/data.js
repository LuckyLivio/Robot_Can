const DEMO_DATA = {
  "cases": [
    {
      "id": "clean_shared_success",
      "label": "三种方法均成功",
      "condition": "clean",
      "state_name": "demo_1000001",
      "eligible_count": 51,
      "video": "videos20/clean_shared_success.mp4",
      "poster": "videos20/clean_shared_success.png",
      "frames": 116,
      "fps": 20,
      "duration_s": 5.8,
      "control_steps": 95,
      "sha256": "badff539539a0cf5e596cac54f260a62c79a8475d697c583b061db308c1a30b3",
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
      "firstFrame": "videos20/clean_shared_success.png"
    },
    {
      "id": "clean_full_only_success",
      "label": "Full成功，BC与Plain未完成",
      "condition": "clean",
      "state_name": "demo_1000026",
      "eligible_count": 1,
      "video": "videos20/clean_full_only_success.mp4",
      "poster": "videos20/clean_full_only_success.png",
      "frames": 421,
      "fps": 20,
      "duration_s": 21.05,
      "control_steps": 400,
      "sha256": "c1680b9a0f69c8de81be67fc4b76641cb807a35426b2f9a1a5ab9110afa60a5a",
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
      "firstFrame": "videos20/clean_full_only_success.png"
    },
    {
      "id": "clean_shared_failure",
      "label": "三种方法均未完成",
      "condition": "clean",
      "state_name": "demo_1000000",
      "eligible_count": 6,
      "video": "videos20/clean_shared_failure.mp4",
      "poster": "videos20/clean_shared_failure.png",
      "frames": 421,
      "fps": 20,
      "duration_s": 21.05,
      "control_steps": 400,
      "sha256": "60b66c7c85c9456415b16478e8e7f25ef44097405a57b8ed0872945668ae5486",
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
      "firstFrame": "videos20/clean_shared_failure.png"
    },
    {
      "id": "noise005_shared_success",
      "label": "三种方法均成功",
      "condition": "noise005",
      "state_name": "demo_1000002",
      "eligible_count": 49,
      "video": "videos20/noise005_shared_success.mp4",
      "poster": "videos20/noise005_shared_success.png",
      "frames": 131,
      "fps": 20,
      "duration_s": 6.55,
      "control_steps": 110,
      "sha256": "88fad24dd38424d04599502532d95fd749c760b9fa3a2ca96a4fcb6922f03a35",
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
      "firstFrame": "videos20/noise005_shared_success.png"
    },
    {
      "id": "noise005_full_only_success",
      "label": "Full成功，BC与Plain未完成",
      "condition": "noise005",
      "state_name": "demo_1000011",
      "eligible_count": 2,
      "video": "videos20/noise005_full_only_success.mp4",
      "poster": "videos20/noise005_full_only_success.png",
      "frames": 421,
      "fps": 20,
      "duration_s": 21.05,
      "control_steps": 400,
      "sha256": "37133f6e0688884af18dabfbe5b4d04a82bd2b1ce650760d7435066f5f5e2e0b",
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
      "firstFrame": "videos20/noise005_full_only_success.png"
    },
    {
      "id": "noise005_shared_failure",
      "label": "三种方法均未完成",
      "condition": "noise005",
      "state_name": "demo_1000000",
      "eligible_count": 8,
      "video": "videos20/noise005_shared_failure.mp4",
      "poster": "videos20/noise005_shared_failure.png",
      "frames": 421,
      "fps": 20,
      "duration_s": 21.05,
      "control_steps": 400,
      "sha256": "76541f9154ab94c5ae57d8130799f5a8bcf477059514c46b0fa73b6ad268528f",
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
      "firstFrame": "videos20/noise005_shared_failure.png"
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
