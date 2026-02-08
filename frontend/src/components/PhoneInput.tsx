"use client";

import { useState, useEffect } from "react";

interface PhoneInputProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  required?: boolean;
  id?: string;
  className?: string;
}

export default function PhoneInput({
  value,
  onChange,
  disabled = false,
  required = false,
  id = "phone",
  className = "",
}: PhoneInputProps) {
  const [displayValue, setDisplayValue] = useState("");

  useEffect(() => {
    // Format phone number for display
    if (value) {
      const cleaned = value.replace(/\D/g, "");
      let formatted = cleaned;
      
      // Format: +63 9XX XXX XXXX or 09XX XXX XXXX
      if (cleaned.startsWith("63")) {
        // +63 9XX XXX XXXX format
        if (cleaned.length <= 2) {
          formatted = `+63`;
        } else if (cleaned.length <= 5) {
          formatted = `+63 ${cleaned.slice(2)}`;
        } else if (cleaned.length <= 8) {
          formatted = `+63 ${cleaned.slice(2, 5)} ${cleaned.slice(5)}`;
        } else {
          formatted = `+63 ${cleaned.slice(2, 5)} ${cleaned.slice(5, 8)} ${cleaned.slice(8, 13)}`;
        }
      } else if (cleaned.startsWith("0")) {
        // 09XX XXX XXXX format (max 11 digits: 0 + 9 + 9)
        if (cleaned.length <= 1) {
          formatted = `0`;
        } else if (cleaned.length <= 4) {
          formatted = `0${cleaned.slice(1)}`;
        } else if (cleaned.length <= 7) {
          formatted = `0${cleaned.slice(1, 4)} ${cleaned.slice(4)}`;
        } else {
          formatted = `0${cleaned.slice(1, 4)} ${cleaned.slice(4, 7)} ${cleaned.slice(7, 11)}`;
        }
      } else if (cleaned.length > 0) {
        // 9XX XXX XXXX format (max 10 digits: 9 + 9)
        if (cleaned.length <= 3) {
          formatted = cleaned;
        } else if (cleaned.length <= 6) {
          formatted = `${cleaned.slice(0, 3)} ${cleaned.slice(3)}`;
        } else {
          formatted = `${cleaned.slice(0, 3)} ${cleaned.slice(3, 6)} ${cleaned.slice(6, 10)}`;
        }
      }
      
      setDisplayValue(formatted);
    } else {
      setDisplayValue("");
    }
  }, [value]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const input = e.target.value;
    // Remove all non-digits
    const cleaned = input.replace(/\D/g, "");
    
    // Limit based on format:
    // +63 9XX XXX XXXX = 13 digits (63 + 9 + 9 digits)
    // 09XX XXX XXXX = 11 digits (0 + 9 + 9 digits)
    // 9XX XXX XXXX = 10 digits (9 + 9 digits)
    let maxDigits = 13;
    if (cleaned.startsWith("0")) {
      maxDigits = 11; // 0 + 9 + 9 digits
    } else if (cleaned.startsWith("63")) {
      maxDigits = 13; // 63 + 9 + 9 digits
    } else if (cleaned.length > 0 && !cleaned.startsWith("63")) {
      maxDigits = 10; // 9 + 9 digits
    }
    
    const limited = cleaned.slice(0, maxDigits);
    
    // Update raw value (without formatting)
    onChange(limited);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    // Allow backspace, delete, tab, escape, enter
    if ([8, 9, 27, 13, 46].indexOf(e.keyCode) !== -1 ||
      // Allow Ctrl+A, Ctrl+C, Ctrl+V, Ctrl+X
      (e.keyCode === 65 && e.ctrlKey === true) ||
      (e.keyCode === 67 && e.ctrlKey === true) ||
      (e.keyCode === 86 && e.ctrlKey === true) ||
      (e.keyCode === 88 && e.ctrlKey === true) ||
      // Allow home, end, left, right
      (e.keyCode >= 35 && e.keyCode <= 39)) {
      return;
    }
    // Ensure that it is a number and stop the keypress
    if ((e.shiftKey || (e.keyCode < 48 || e.keyCode > 57)) && (e.keyCode < 96 || e.keyCode > 105)) {
      e.preventDefault();
    }
  };

  return (
    <div className="relative">
      <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
        <span className="text-gray-500 text-sm">🇵🇭</span>
      </div>
      <input
        type="tel"
        id={id}
        value={displayValue}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder="+63 9XX XXX XXXX or 09XX XXX XXXX"
        required={required}
        disabled={disabled}
        maxLength={17} // +63 9XX XXX XXXX = 17 chars
        className={`pl-10 ${className} w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed text-gray-900`}
      />
    </div>
  );
}
