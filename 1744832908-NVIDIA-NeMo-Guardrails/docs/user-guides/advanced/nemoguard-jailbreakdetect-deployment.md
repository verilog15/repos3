# NemoGuard JailbreakDetect Deployment

The NemoGuard Jailbreak Detect model is available via the [Jailbreak Detection Container](jailbreak-detection-deployment.md) or as an [NVIDIA NIM](https://docs.nvidia.com/nim/#nemoguard).

## NIM Deployment

The first step is to ensure access to NVIDIA NIM assets through NGC using an NVAIE license.
Once you have the NGC API key with the necessary permissions, set the following environment variables:

```bash
export NGC_API_KEY=<your NGC API key>
docker login nvcr.io -u '$oauthtoken' -p <<< <your NGC API key>
```

Test that you are able to use the NVIDIA NIM assets by pulling the latest NemoGuard container.

```bash
export NIM_IMAGE='nvcr.io/nim/nvidia/nemoguard-jailbreak-detect:latest'
docker pull $NIM_IMAGE
```

Then run the container.

```bash
docker run -it --gpus=all --runtime=nvidia \
    -e NGC_API_KEY="$NGC_API_KEY" \
    -p 8000:8000 \
    $NIM_IMAGE
```

## Using the NIM in Guardrails
Within your guardrails configuration file, you can specify that you want to use the NIM endpoint as part of the jailbreak detection configuration.
To do this, ensure that you specify the location of the NIM in the `nim_url` parameter.
If the NIM is listening on a port other than 8000, specify that port in the `nim_port` parameter.
An example configuration is shown below.

```yaml
models:
  - type: main
    engine: openai
    model: gpt-3.5-turbo-instruct



rails:
  config:
    jailbreak_detection:
      nim_url: "0.0.0.0"
      nim_port: 8000
  input:
    flows:
      - jailbreak detection model
```
