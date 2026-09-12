---
type: "query"
date: "2026-09-10T13:17:53.620936+00:00"
question: "Phase 2 RTSP camera live preview reconnect ROI implementation should connect to which existing modules and contracts?"
contributor: "graphify"
outcome: "useful"
source_nodes: ["CameraProvider", "CameraFrame", "Camera", "ConfigurationService", "Phase 2 Camera"]
---

# Q: Phase 2 RTSP camera live preview reconnect ROI implementation should connect to which existing modules and contracts?

## Answer

Expanded from original query via graph vocab: [camera, provider, phase, connect, contracts, configuration, settings, api, database]. Phase 2 should extend CameraProvider and CameraFrame, persist field configuration on Camera through a repository and versioned API, compose lifecycle services in main.py, and replace the Cameras UI placeholder while keeping detector/OCR boundaries untouched.

## Outcome

- Signal: useful

## Source Nodes

- CameraProvider
- CameraFrame
- Camera
- ConfigurationService
- Phase 2 Camera