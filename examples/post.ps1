$ErrorActionPreference = "Stop"
$env:OPENCV_IO_ENABLE_OPENEXR = "1"

$InputExr = ".\Render\BF3_PrePost_HDR\Image0000.exr"
$OutputPng = ".\Render\Final\Image0000_BF3.png"
$StageDir = ".\Render\Final\Stages"

New-Item -ItemType Directory -Force (Split-Path $OutputPng) | Out-Null

py .\src\bf3_post.py `
  $InputExr `
  --lut .\private\colorGradingTexture.dds `
  --grain .\private\filmGrainTexture.png `
  --exposure-ev -0.5 `
  -o $OutputPng `
  --stages $StageDir
