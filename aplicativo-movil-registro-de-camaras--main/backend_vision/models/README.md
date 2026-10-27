# Face recognition models

The backend uses OpenCV Zoo's YuNet face detector and SFace face recognizer.
Both ONNX files are included so the backend can start without downloading model
weights at runtime.

| Model | Upstream source | License |
| --- | --- | --- |
| `face_detection_yunet_2023mar.onnx` | [OpenCV Zoo YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) | [MIT](./LICENSE.YuNet.txt) |
| `face_recognition_sface_2021dec.onnx` | [OpenCV Zoo SFace](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface) | [Apache 2.0](./LICENSE.SFace.txt) |
