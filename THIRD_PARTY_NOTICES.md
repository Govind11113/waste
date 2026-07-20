# Third-party notices for the Windows release

This notice records the major model and online-service assets deliberately added for the localhost release. Python/JavaScript libraries bundled by the build remain governed by their own licenses and metadata; their inclusion does not relicense this project.

## Google SigLIP 2 classifier snapshot

- Model: `google/siglip2-base-patch16-224`
- Exact revision: `75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2`
- Task used here: zero-shot image classification
- Upstream model card: <https://huggingface.co/google/siglip2-base-patch16-224/tree/75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2>
- Upstream-declared license: Apache License 2.0

The release snapshot includes:

- `models/classifier/siglip2-base/MODEL_METADATA.json`;
- the upstream `README.md` model card;
- `LICENSE.apache-2.0.txt`; and
- `model_manifest.json`, which SHA-256 covers every distributed snapshot file.

The model is pre-trained third-party material. Its presence does not establish classifier accuracy for this project's target population, and no committed held-out real-image benchmark is claimed.

## Online authentication and regional map

- Clerk provides development authentication under Clerk's current service terms and privacy materials. It is contacted online at runtime; no Clerk secret key is bundled.
- Weather readings use the Open-Meteo API under that provider's current terms/attribution requirements.
- Map tiles can come from OpenStreetMap, OpenTopoMap, or CARTO. Attribution is rendered in the map control and must not be removed.

Service terms and endpoints can change independently of this release. Review current provider terms before operational deployment.

## Lifespan artifacts

The bundled RF, XGBoost, and LightGBM pipeline artifacts were generated within this project from synthetic data and are integrity-covered by `models/lifespan/model_manifest.json`. They are comparison/prototype artifacts, not externally validated field models.
