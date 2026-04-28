/**
 * Context Multi-Tenant pour OptiBoard
 * ====================================
 * Gestion du DWH actif et des societes accessibles
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { extractErrorMessage } from '../services/api';

const DWHContext = createContext(null);

export const useDWH = () => {
  const context = useContext(DWHContext);
  if (!context) {
    throw new Error('useDWH must be used within a DWHProvider');
  }
  return context;
};

export const DWHProvider = ({ children }) => {
  // DWH actif
  const [currentDWH, setCurrentDWH] = useState(null);
  const [dwhList, setDwhList] = useState([]);

  // Societes
  const [societesList, setSocietesList] = useState([]);
  const [selectedSociete, setSelectedSociete] = useState(null); // null = toutes

  // Etat
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Charger la liste des DWH accessibles
  const loadDWHList = useCallback(async (userId) => {
    try {
      const response = await axios.get('/api/auth/dwh-list', {
        headers: { 'X-User-Id': userId }
      });
      setDwhList(response.data || []);
      return response.data || [];
    } catch (err) {
      console.error('Erreur chargement DWH list:', err);
      setError('Erreur lors du chargement des DWH');
      return [];
    }
  }, []);

  // Charger les societes du DWH actif
  const loadSocietes = useCallback(async (userId, dwhCode) => {
    if (!dwhCode) {
      setSocietesList([]);
      return [];
    }

    try {
      const response = await axios.get('/api/auth/societes-list', {
        headers: {
          'X-User-Id': userId,
          'X-DWH-Code': dwhCode
        }
      });
      const societes = response.data || [];
      setSocietesList(societes);
      return societes;
    } catch (err) {
      console.error('Erreur chargement societes:', err);
      setSocietesList([]);
      return [];
    }
  }, []);

  // Changer de DWH
  const switchDWH = useCallback(async (userId, dwhCode) => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.post('/api/auth/switch-dwh',
        { dwh_code: dwhCode },
        { headers: { 'X-User-Id': userId } }
      );

      if (response.data.success) {
        const newDWH = response.data.current_dwh;
        setCurrentDWH(newDWH);

        // Charger les societes du nouveau DWH
        await loadSocietes(userId, dwhCode);

        // Reset le filtre societe
        setSelectedSociete(null);

        // Sauvegarder dans localStorage
        localStorage.setItem('currentDWH', JSON.stringify(newDWH));

        return { success: true, dwh: newDWH };
      }
    } catch (err) {
      const message = extractErrorMessage(err, 'Erreur lors du changement de DWH');
      setError(message);
      return { success: false, error: message };
    } finally {
      setLoading(false);
    }
  }, [loadSocietes]);

  // Changer de societe (filtre)
  const switchSociete = useCallback(async (userId, dwhCode, societeCode) => {
    try {
      const response = await axios.post('/api/auth/switch-societe',
        { societe_code: societeCode },
        {
          headers: {
            'X-User-Id': userId,
            'X-DWH-Code': dwhCode
          }
        }
      );

      if (response.data.success) {
        setSelectedSociete(societeCode);
        localStorage.setItem('selectedSociete', societeCode || '');
        return { success: true };
      }
    } catch (err) {
      const message = extractErrorMessage(err, 'Erreur lors du changement de societe');
      setError(message);
      return { success: false, error: message };
    }
  }, []);

  // Initialiser le contexte depuis le localStorage ou le login
  const initializeContext = useCallback(async (userId, contextData) => {
    setLoading(true);

    try {
      // Charger la liste des DWH
      const dwhs = await loadDWHList(userId);

      if (contextData?.current_dwh) {
        // Utiliser le DWH du contexte de login
        setCurrentDWH(contextData.current_dwh);
        localStorage.setItem('currentDWH', JSON.stringify(contextData.current_dwh));

        // Charger les societes
        if (contextData.current_dwh.code) {
          await loadSocietes(userId, contextData.current_dwh.code);
        }
      } else {
        // Essayer de recuperer depuis localStorage
        const savedDWH = localStorage.getItem('currentDWH');
        let restoredFromStorage = false;
        if (savedDWH) {
          try {
            const parsedDWH = JSON.parse(savedDWH);
            // Verifier que le DWH est valide (code non null) et accessible
            if (parsedDWH?.code) {
              const hasAccess = dwhs.some(d => d.code === parsedDWH.code);
              if (hasAccess) {
                setCurrentDWH(parsedDWH);
                await loadSocietes(userId, parsedDWH.code);
                restoredFromStorage = true;
              }
            } else {
              // localStorage corrompu (ex: {code: null}), nettoyer
              localStorage.removeItem('currentDWH');
            }
          } catch {
            localStorage.removeItem('currentDWH');
          }
        }
        if (!restoredFromStorage && dwhs.length > 0) {
          // Prendre le DWH par defaut ou le premier
          const defaultDWH = dwhs.find(d => d.is_default) || dwhs[0];
          const dwhData = { code: defaultDWH.code, nom: defaultDWH.nom };
          setCurrentDWH(dwhData);
          localStorage.setItem('currentDWH', JSON.stringify(dwhData));
          await loadSocietes(userId, defaultDWH.code);
        }
      }

      // Restaurer la societe selectionnee
      const savedSociete = localStorage.getItem('selectedSociete');
      if (savedSociete) {
        setSelectedSociete(savedSociete);
      }

    } catch (err) {
      console.error('Erreur initialisation contexte DWH:', err);
      setError('Erreur lors de l\'initialisation');
    } finally {
      setLoading(false);
    }
  }, [loadDWHList, loadSocietes]);

  // Restaurer depuis localStorage au montage (ex: après refresh de page)
  useEffect(() => {
    if (currentDWH) return  // déjà initialisé via initializeContext
    const savedDWH = localStorage.getItem('currentDWH')
    if (savedDWH) {
      try {
        const parsed = JSON.parse(savedDWH)
        // Ne restaurer que si le code DWH est valide (pas null)
        if (parsed?.code) {
          setCurrentDWH(parsed)
        } else {
          localStorage.removeItem('currentDWH')
        }
      } catch {
        localStorage.removeItem('currentDWH')
      }
    }
    const savedSociete = localStorage.getItem('selectedSociete')
    if (savedSociete) setSelectedSociete(savedSociete)
    setLoading(false)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Reset le contexte (logout)
  const resetContext = useCallback(() => {
    setCurrentDWH(null);
    setDwhList([]);
    setSocietesList([]);
    setSelectedSociete(null);
    setError(null);
    localStorage.removeItem('currentDWH');
    localStorage.removeItem('selectedSociete');
  }, []);

  // Headers HTTP avec le contexte
  const getContextHeaders = useCallback((userId) => {
    const headers = {};
    if (userId) headers['X-User-Id'] = userId;
    if (currentDWH?.code) headers['X-DWH-Code'] = currentDWH.code;
    if (selectedSociete) headers['X-Societe-Code'] = selectedSociete;
    return headers;
  }, [currentDWH, selectedSociete]);

  // Filtre societe pour les requetes
  const getSocieteFilter = useCallback(() => {
    if (selectedSociete) {
      return [selectedSociete];
    }
    return societesList.map(s => s.code_societe || s.societe_code);
  }, [selectedSociete, societesList]);

  const value = {
    // DWH
    currentDWH,
    dwhList,
    switchDWH,

    // Societes
    societesList,
    selectedSociete,
    switchSociete,
    getSocieteFilter,

    // Etat
    loading,
    error,

    // Fonctions
    initializeContext,
    resetContext,
    loadDWHList,
    loadSocietes,
    getContextHeaders,

    // Helper
    hasDWH: !!currentDWH?.code,
    hasMultipleDWH: dwhList.length > 1,
    hasMultipleSocietes: societesList.length > 1
  };

  return (
    <DWHContext.Provider value={value}>
      {children}
    </DWHContext.Provider>
  );
};

export default DWHContext;
