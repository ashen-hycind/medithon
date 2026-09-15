import React from 'react';
import { UserProfile, BloodGroupType, SexType } from '../types';

export interface OnboardingState {
  step: 1 | 2 | 3 | 4;
  dob: string;
  sex: SexType;
  bloodGroup: BloodGroupType;
  heightCm: number;
  heightUnit: 'cm' | 'ft';
  weightKg: number;
  weightUnit: 'kg' | 'lbs';
  activityLevel: number;
  occupation: string;
  isPregnant: boolean;
  gestationalWeeks: number;
}
