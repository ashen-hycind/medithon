# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React / Vite with Tailwind CSS (Lucide icons, modern responsive layout)

## Users

- **Primary**: Individuals regularly monitoring chronic or long-term health metrics at home (hypertension, diabetes, respiratory, weight, kidney health).
- **Secondary**: Family caregivers monitoring metrics for elderly relatives, children, or dependents.
- **Healthcare Providers**: Physicians and clinicians who need clear, longitudinal health trend views without vendor lock-in.

## Product Purpose

Transform fragmented personal health measurements across heterogeneous devices (blood pressure cuffs, glucometers, pulse oximeters, smart scales, test strips) into a single trusted, longitudinal health record that both patients and healthcare providers can understand and act upon.

## Positioning

Device-agnostic personal health data unifier: solves fragmentation and interoperability, not just OCR or one-off measurement capture, turning everyday home readings into a continuous clinical-grade health picture.

## Operating Context

- Mobile and desktop web access.
- Quick capture via camera OCR, screenshots, device sync, and manual entry.
- Direct review and validation of measurements before storage.
- High-trust medical records requiring clarity, calm visual precision, and privacy.

## Capabilities and Constraints

- **Scope for current surface**: Landing page displaying the core problem, mission/motto, and interactive Login / Create Account modal dialogs.
- **Auth presentation**: Direct modal dialogs / overlays on the landing page keeping the user in context.
- **Backend API**: FastAPI / Python backend located in `/backend` with Firebase Auth and Firestore integration.

## Product Principles

1. **Clarity Over Clutter**: Medical data and intent must be calm, immediate, and unambiguous.
2. **Empowering & Device-Agnostic**: Works with any device the user already owns.
3. **High-Integrity & Trust**: Secure, private, and grounded in clinician-understandable longitudinal data.
