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
        formatted = `+63 ${cleaned.slice(2)}`;
        if (cleaned.length > 3) {
          formatted = `+63 ${cleaned.slice(2, 5)}`;
          if (cleaned.length > 5) {
            formatted = `+63 ${cleaned.slice(2, 5)} ${cleaned.slice(5, 8)}`;
            if (cleaned.length > 8) {
              formatted = `+63 ${cleaned.slice(2, 5)} ${cleaned.slice(5, 8)} ${cleaned.slice(8)}`;
            }
          }
        }
      } else if (cleaned.startsWith("0")) {
        formatted = `0${cleaned.slice(1)}`;
        if (cleaned.length > 3) {
          formatted = `0${cleaned.slice(1, 4)}`;
          if (cleaned.length > 4) {
            formatted = `0${cleaned.slice(1, 4)} ${cleaned.slice(4, 7)}`;
            if (cleaned.length > 7) {
              formatted = `0${cleaned.slice(1, 4)} ${cleaned.slice(4, 7)} ${cleaned.slice(7)}`;
            }
          }
        }
      } else if (cleaned.length > 0) {
        formatted = cleaned;
        if (cleaned.length > 3) {
          formatted = `${cleaned.slice(0, 3)} ${cleaned.slice(3, 6)}`;
          if (cleaned.length > 6) {
            formatted = `${cleaned.slice(0, 3)} ${cleaned.slice(3, 6)} ${cleaned.slice(6)}`;
          }
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
    
    // Limit to 13 digits (for +63 9XX XXX XXXX)
    const limited = cleaned.slice(0, 13);
    
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
