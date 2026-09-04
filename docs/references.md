# References

Papers, tools, and models this project builds on.

---

## Core architecture

**A hybrid tendon-driven continuum robot that avoids torsion under external load**
Maria Paula Huertas Niño, Mohamed Boutayeb, Dominique Martinez.
*Frontiers in Robotics and AI* 12:1576209, 2025. Open access (CC BY).
[doi:10.3389/frobt.2025.1576209](https://doi.org/10.3389/frobt.2025.1576209)

> The key justification for this project's architecture. Bending from a
> **single tendon** with lateral joints constraining the bending plane, plus a
> **rotary base** for orientation. Reports negligible out-of-plane deviation
> (millimetre range), *smaller* in-plane tip deflection than a 4-tendon
> continuum robot, and a 450 g payload. This is why "1 cable + rotation" is
> treated here as a sound choice rather than a simplification.

**SpiRobs: Logarithmic spiral-shaped robots for versatile grasping across scales**
Zhanchi Wang, Nikolaos M. Freris, Xi Wei.
*Device* 3, 100646, 2025.
[doi:10.1016/j.device.2024.100646](https://doi.org/10.1016/j.device.2024.100646)

> The tentacle geometry. A log-spiral taper actuated by two or three cables,
> 3D printed in TPU, with an octopus-inspired grasping strategy. The tip curls
> first and the body follows, so the tentacle wraps rather than pushes.

**3D printed cable-driven continuum robots with generally routed cables: modeling and experiments**
Soumya Kanti Mahapatra, Ashwin K. P., Ashitava Ghosal. arXiv, 2020.
[arXiv:2003.04593](https://arxiv.org/abs/2003.04593)

> Background on cable-driven continuum robots: how cable routing determines the
> achievable shapes, and kinematic vs. Cosserat-rod modelling of the result.

**Design and Experiment of a Soft Gripper Based on Cable-Driven Continuum Structures**
Qiong Wu, Zhenglong Yi, Hongqiang Wang, Han Yuan. IEEE ROBIO 2021.
[doi:10.1109/ROBIO54168.2021.9739279](https://doi.org/10.1109/ROBIO54168.2021.9739279)

> A five-finger soft gripper built from cable-driven continuum fingers, with
> stiffness deliberately redistributed along each finger so it envelops an
> object instead of bending uniformly, which is relevant to the spine-thickness choice
> made here.

---

## FEM modelling and control (Inria / DEFROST)

**Optimization-Based Inverse Model of Soft Robots With Contact Handling**
Eulalie Coevoet, Adrien Escande, Christian Duriez.
*IEEE Robotics and Automation Letters*, 2017.
[doi:10.1109/LRA.2017.2669367](https://doi.org/10.1109/LRA.2017.2669367) ·
[hal-01500912](https://inria.hal.science/hal-01500912v1)

**Soft robots locomotion and manipulation control using FEM simulation and quadratic programming**
Eulalie Coevoet, Adrien Escande, Christian Duriez.
IEEE RoboSoft 2019.
[doi:10.1109/ROBOSOFT.2019.8722815](https://doi.org/10.1109/ROBOSOFT.2019.8722815) ·
[hal-02079151](https://inria.hal.science/hal-02079151v1)

> The research-grade control path: simulate the soft body with FEM in SOFA and
> solve an optimisation for the actuation that achieves a desired pose. Out of
> scope for this internship.

---

## Software and tools

| Resource | Use here |
|---|---|
| [LeRobot](https://github.com/huggingface/lerobot) (v0.6.0) | Robot drivers, teleoperation, dataset recording, ACT training |
| [SOFA Framework](https://www.sofa-framework.org/) | FEM simulation of soft bodies (future work) |
| [SOFA SoftRobots plugin](https://project.inria.fr/softrobot/) | Soft-robot modelling and inverse control in SOFA |

## Hardware sources

| Resource | Use here |
|---|---|
| [SO-ARM100 / SO-101](https://github.com/TheRobotStudio/SO-ARM100) | The base arm. Stock parts, print files, and the gripper this project replaces |
| [Shoggoth Mini](https://github.com/mlecauchois/shoggoth-mini) | A SpiRob tentacle running on the same STS3215 servos and LeRobot. The reference I sized the tentacle against |
| [Open-Spiral-Robots (OpenSpiRobs)](https://github.com/ZhanchiWang/Open-Spiral-Robots) | The parametric design tool used to generate the tentacle body (PolyForm Noncommercial 1.0.0) |
