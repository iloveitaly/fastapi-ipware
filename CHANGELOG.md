# Changelog

## [0.2.1](https://github.com/iloveitaly/fastapi-ipware/compare/v0.2.0...v0.2.1) (2026-09-26)


### Documentation

* clarify trusted and proxy_count in code examples ([81cb8b7](https://github.com/iloveitaly/fastapi-ipware/commit/81cb8b705e507a6a2fb0745e5617f1caf03d9fcc))

## [0.2.0](https://github.com/iloveitaly/fastapi-ipware/compare/v0.1.2...v0.2.0) (2026-09-25)


### Features

* add dependency injection helpers and ASGI middleware ([960733a](https://github.com/iloveitaly/fastapi-ipware/commit/960733aa1d32128ee0e20bc7dd4dbd8a685a8b66))
* upgrade to python-ipware v4 and expand header support ([de8d2c3](https://github.com/iloveitaly/fastapi-ipware/commit/de8d2c30d84250fe3b085d3d9f0bd492916b23ae))


### Documentation

* add developer guidelines and commands documentation ([721c3bd](https://github.com/iloveitaly/fastapi-ipware/commit/721c3bda739e5d2dd3e995a823668b0a7a6bba56))
* remove agent coding instructions ([0c5daaf](https://github.com/iloveitaly/fastapi-ipware/commit/0c5daaf0f3def7a3b34e357694c863d41247cb33))
* update quick start and usage examples in README ([4835f22](https://github.com/iloveitaly/fastapi-ipware/commit/4835f22cc592f30f5545b2ec956c095aca84c7a2))

## [0.1.2](https://github.com/iloveitaly/fastapi-ipware/compare/v0.1.1...v0.1.2) (2026-01-23)


### Bug Fixes

* include REMOTE_ADDR correctly in header precedence ([1de59e4](https://github.com/iloveitaly/fastapi-ipware/commit/1de59e49ca85dc8cb46ea2c73a3cba4a51acd64e))


### Documentation

* simplify readme ([b03b266](https://github.com/iloveitaly/fastapi-ipware/commit/b03b2664389bb0c6fa0631c4956d03891baad64f))
* update credits section with additional link ([0e68726](https://github.com/iloveitaly/fastapi-ipware/commit/0e68726c861b2f3b400c68e33d891fdc6af36fc0))

## [0.1.1](https://github.com/iloveitaly/fastapi-ipware/compare/v0.1.0...v0.1.1) (2025-11-01)


### Bug Fixes

* prioritize provider headers over generic for client IP ([f40e4c8](https://github.com/iloveitaly/fastapi-ipware/commit/f40e4c822386f2499ccbb193e4d91615f32b4455))

## 0.1.0 (2025-10-31)


### Features

* add FastAPIIpWare for header-native IP extraction ([bb0e73f](https://github.com/iloveitaly/fastapi-ipware/commit/bb0e73fe624d234506539827f854213b068bf68d))


### Bug Fixes

* always assert ip is not None in ipware tests ([62eaf77](https://github.com/iloveitaly/fastapi-ipware/commit/62eaf77a0994cbb8946ac74dd7ebd70fd8dd0f47))


### Documentation

* add coding rules, instructions, and prompts for dev workflow ([a3ac6d0](https://github.com/iloveitaly/fastapi-ipware/commit/a3ac6d01e68613d8c16e79939cc256a4b0783d15))
* add FastAPI example using fastapi-ipware for client IP ([b38385e](https://github.com/iloveitaly/fastapi-ipware/commit/b38385ec009486dab967696b171a024c4fbbff60))
* add implementation summary and clarify license link in README ([b7adc17](https://github.com/iloveitaly/fastapi-ipware/commit/b7adc1732c8ff3baa9fe47fd9347bdf995c1fcf3))
* add MIT license to LICENSE.md file ([d75319d](https://github.com/iloveitaly/fastapi-ipware/commit/d75319d004f4aecf56feb04bbbfee18a78a143f5))
* add README with usage, features, and examples ([e097c67](https://github.com/iloveitaly/fastapi-ipware/commit/e097c67547a89e6d7b93b10cc8f3d6bf89f1616f))
* link to default header precedence config in README ([7aeb558](https://github.com/iloveitaly/fastapi-ipware/commit/7aeb5587ee89e8343198d287cc5981f15db60ad6))
* simplify explanation of header handling in README ([c269bf9](https://github.com/iloveitaly/fastapi-ipware/commit/c269bf9c397f4622265bad448062634c70f7eb46))
