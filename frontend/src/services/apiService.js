import axios from 'axios';

const API_BASE_URL = 'http://localhost:8002';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Fetch all pending AI action proposals from the backend.
 * @returns {Promise<Array>} Array of pending proposals
 */
export const fetchPendingProposals = async () => {
  try {
    const response = await apiClient.get('/proposals/pending');
    return response.data;
  } catch (error) {
    console.error('Error fetching pending proposals:', error.message);
    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response data:', error.response.data);
    }
    throw error;
  }
};

/**
 * Approve an AI action proposal.
 * @param {string} proposalId - The UUID of the proposal to approve
 * @returns {Promise<Object>} Approval response data
 */
export const approveProposal = async (proposalId) => {
  try {
    const response = await apiClient.post(`/proposals/${proposalId}/approve`);
    return response.data;
  } catch (error) {
    console.error(`Error approving proposal ${proposalId}:`, error.message);
    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response data:', error.response.data);
    }
    throw error;
  }
};

/**
 * Reject an AI action proposal with feedback.
 * @param {string} proposalId - The UUID of the proposal to reject
 * @param {string} rejectionReason - Explanation for rejection
 * @param {string} reviewerId - Identifier of the human reviewer
 * @returns {Promise<Object>} Rejection response data
 */
export const rejectProposal = async (proposalId, rejectionReason, reviewerId) => {
  try {
    const response = await apiClient.post(`/proposals/${proposalId}/reject`, {
      rejection_reason: rejectionReason,
      reviewer_id: reviewerId,
    });
    return response.data;
  } catch (error) {
    console.error(`Error rejecting proposal ${proposalId}:`, error.message);
    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response data:', error.response.data);
    }
    throw error;
  }
};

/**
 * Create a new ticket via webhook.
 * @param {Object} ticketData - The ticket data
 * @param {string} ticketData.customer_id - Customer identifier
 * @param {string} ticketData.message_body - Initial message content
 * @param {string} ticketData.priority_level - Priority level (low, medium, high, critical)
 * @returns {Promise<Object>} Created ticket data
 */
export const createTicket = async (ticketData) => {
  try {
    const response = await apiClient.post('/webhook/ticket', ticketData);
    return response.data;
  } catch (error) {
    console.error('Error creating ticket:', error.message);
    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response data:', error.response.data);
    }
    throw error;
  }
};

export default {
  fetchPendingProposals,
  approveProposal,
  rejectProposal,
  createTicket,
};
