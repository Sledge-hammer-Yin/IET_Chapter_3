# Storage

Code, documentation, figures and small results: 1.48 MiB (excluding Git metadata and Python caches).
Shared processed data outside the repository: 5.95 MiB.
Isolated Python/GTSAM environment, including bytecode caches: 1089.4 MiB of logical file sizes.
External pinned RTKLIB frontend: 39.5 MiB.
C: free space after cleanup: 65.57 GiB.

The task installation cache and diagnostic smoke outputs were removed. The environment was checked again after cleanup. Raw downloads and existing Conda environments were not deleted or changed. No ROS bags, point clouds, duplicate raw CSVs, covariance histories or full graph dumps are generated. Later runs reuse shared inputs and overwrite the same small result files. Keep data, environments and upstream code outside the GitHub repository; the ignore rules also protect common accidental placements inside it.
