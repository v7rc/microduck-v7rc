# Third-party notices / 第三方授權聲明

A formal license for this repository’s original integration code and scenes is pending.
The following notices cover their respective third-party components.

## Shipped in the installers

- Both installers ship patches to Pollen Robotics’ Microduck launcher script, from the revision pinned in `upstream-revisions.json`. The patches mark the changes for choosing the simulator body module and overriding the walking policy path. The upstream code is licensed under Apache-2.0. The full license is included as `licenses/Apache-2.0.txt` in the application payload and as `Apache-2.0.txt` in the launcher notices. [Pollen Robotics Microduck license](https://github.com/pollen-robotics/microduck/blob/98ce17e4868ba9370713c4d11f3d934e5a1b7687/LICENSE).
- The self-contained Windows installer includes Microsoft .NET and the Windows Desktop runtime (WPF), plus the native .NET app host. The .NET runtime and app host share the same license and notices. The launcher’s third-party notices folder includes those files from the resolved .NET runtime pack, plus the WPF license and matching upstream notices. [Microsoft .NET license](https://github.com/dotnet/runtime/blob/main/LICENSE.TXT) · [Microsoft WPF license](https://github.com/dotnet/wpf/blob/main/LICENSE.TXT).
- The macOS launcher links to the macOS system frameworks and system Swift libraries. Its notices and Apache license are available in the DMG and in the app resources.

## Downloaded by setup

- MuJoCo 3.10.0 is downloaded as a Python wheel. It is licensed under Apache-2.0. Its license and applicable third-party notices are provided in the installed wheel metadata. [MuJoCo license](https://raw.githubusercontent.com/google-deepmind/mujoco/3.10.0/LICENSE).
- Setup retrieves the pinned Microduck runtime and Microduck RL source. Their Apache-2.0 license files remain in their respective checkouts. The Microduck RL STL files listed in its model license are licensed separately under CC BY-NC-SA 4.0. Commercial use of those meshes requires separate permission or a suitable replacement. [Microduck RL model license](https://github.com/pollen-robotics/microduck_rl/blob/bae39f5900b318f7e87fc485c30a31213cfa14eb/LICENSE-MODELS.md).
- Setup downloads the official ONNX policy set, microduck-policies v8, which Pollen Robotics labels Apache-2.0. [Official v8 policy set](https://huggingface.co/pollen-robotics/microduck-policies/tree/v8).
- Setup tools and other dependencies are retrieved from their respective upstream sources and retain their own license files. An offline distribution that bundles these dependencies must include the applicable license texts and notices for what it ships.
