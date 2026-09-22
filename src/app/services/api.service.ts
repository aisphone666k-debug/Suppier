import { Injectable } from '@angular/core';

export interface VerifyEmployeeResponse {
  success: boolean;
  message: string;
  user?: {
    employeeId: string;
    fullName: string;
    department: string;
    role: string;
  };
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = 'http://localhost:5000/api';

  /**
   * Verify 5-digit employee ID with backend API
   */
  async verifyEmployee(employeeId: string): Promise<VerifyEmployeeResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/auth/verify-employee`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ employeeId })
      });

      const data = await response.json();
      return data;
    } catch (err) {
      console.warn('Backend API offline or unreachable, using local fallback:', err);
      // Fallback check if backend server is not running yet
      const validMock = ['BPT01', 'MA105', 'GM101', 'PMA01', '12345'];
      const code = employeeId.toUpperCase();
      if (validMock.includes(code) || code.startsWith('BPT') || code.startsWith('MA')) {
        return {
          success: true,
          message: 'เข้าสู่ระบบสำเร็จ (Local Mode)',
          user: {
            employeeId: code,
            fullName: `พนักงานรหัส ${code}`,
            department: 'Manufacturing',
            role: 'Staff'
          }
        };
      } else {
        return {
          success: false,
          message: 'รหัสพนักงานไม่ถูกต้อง'
        };
      }
    }
  }

  /**
   * Fetch all requisition items from Database
   */
  async getRequisitionItems(): Promise<any[]> {
    try {
      const response = await fetch(`${this.baseUrl}/requisition/items`);
      const result = await response.json();
      return result.data || [];
    } catch (err) {
      console.warn('Backend API offline, using local requisition data:', err);
      return [];
    }
  }

  /**
   * Save or update requisition item
   */
  async saveRequisitionItem(item: any): Promise<boolean> {
    try {
      const url = item.id ? `${this.baseUrl}/requisition/items/${item.id}` : `${this.baseUrl}/requisition/items`;
      const method = item.id ? 'PUT' : 'POST';
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item)
      });
      const res = await response.json();
      return !!res.success;
    } catch (err) {
      console.error('Failed to save requisition item to backend:', err);
      return false;
    }
  }
}
