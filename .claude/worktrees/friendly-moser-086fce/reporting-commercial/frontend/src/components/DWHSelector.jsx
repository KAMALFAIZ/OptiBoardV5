/**
 * Composant Selecteur DWH + Societe
 * ==================================
 * Barre de selection pour changer de DWH et filtrer par societe
 */

import React, { useState, useRef, useEffect } from 'react';
import { Building2, ChevronDown, Check, Store, Filter, X } from 'lucide-react';
import { useDWH } from '../context/DWHContext';
import { useAuth } from '../context/AuthContext';

const DWHSelector = ({ className = '' }) => {
  const { user } = useAuth();
  const {
    currentDWH,
    dwhList,
    switchDWH,
    societesList,
    selectedSociete,
    switchSociete,
    loading,
    hasMultipleDWH,
    hasMultipleSocietes
  } = useDWH();

  const [dwhDropdownOpen, setDwhDropdownOpen] = useState(false);
  const [societeDropdownOpen, setSocieteDropdownOpen] = useState(false);
  const dwhRef = useRef(null);
  const societeRef = useRef(null);

  // Fermer les dropdowns au clic exterieur
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dwhRef.current && !dwhRef.current.contains(event.target)) {
        setDwhDropdownOpen(false);
      }
      if (societeRef.current && !societeRef.current.contains(event.target)) {
        setSocieteDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Changer de DWH
  const handleDWHChange = async (dwhCode) => {
    if (!user?.id || dwhCode === currentDWH?.code) return;

    const result = await switchDWH(user.id, dwhCode);
    if (result.success) {
      setDwhDropdownOpen(false);
      // Rafraichir la page pour recharger les donnees
      window.location.reload();
    }
  };

  // Changer de societe
  const handleSocieteChange = async (societeCode) => {
    if (!user?.id || !currentDWH?.code) return;

    const result = await switchSociete(user.id, currentDWH.code, societeCode);
    if (result.success) {
      setSocieteDropdownOpen(false);
      // Declencher un event pour rafraichir les donnees
      window.dispatchEvent(new CustomEvent('societe-changed', { detail: { societeCode } }));
    }
  };

  // Ne pas afficher si pas de DWH
  if (!currentDWH) {
    return null;
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Selecteur DWH */}
      <div className="relative" ref={dwhRef}>
        <button
          onClick={() => hasMultipleDWH && setDwhDropdownOpen(!dwhDropdownOpen)}
          disabled={loading || !hasMultipleDWH}
          className={`
            flex items-center gap-2 px-3 py-1.5 rounded-lg
            bg-primary-50 dark:bg-primary-900/30
            text-primary-700 dark:text-primary-300
            border border-primary-200 dark:border-primary-700
            ${hasMultipleDWH ? 'hover:bg-primary-100 dark:hover:bg-primary-900/50 cursor-pointer' : 'cursor-default'}
            transition-colors text-sm font-medium
          `}
        >
          <Building2 size={16} />
          <span className="max-w-[150px] truncate">{currentDWH.nom}</span>
          {hasMultipleDWH && (
            <ChevronDown
              size={14}
              className={`transition-transform ${dwhDropdownOpen ? 'rotate-180' : ''}`}
            />
          )}
        </button>

        {/* Dropdown DWH */}
        {dwhDropdownOpen && hasMultipleDWH && (
          <div className="absolute top-full left-0 mt-1 w-64 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50 overflow-hidden">
            <div className="py-1 max-h-64 overflow-y-auto">
              {dwhList.map((dwh) => (
                <button
                  key={dwh.code}
                  onClick={() => handleDWHChange(dwh.code)}
                  className={`
                    w-full px-4 py-2 text-left flex items-center justify-between
                    hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors
                    ${dwh.code === currentDWH?.code ? 'bg-primary-50 dark:bg-primary-900/30' : ''}
                  `}
                >
                  <div className="flex items-center gap-2">
                    <Building2 size={16} className="text-gray-400" />
                    <div>
                      <div className="font-medium text-sm text-gray-900 dark:text-white">
                        {dwh.nom}
                      </div>
                      {dwh.raison_sociale && (
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {dwh.raison_sociale}
                        </div>
                      )}
                    </div>
                  </div>
                  {dwh.code === currentDWH?.code && (
                    <Check size={16} className="text-primary-600" />
                  )}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Separateur */}
      {hasMultipleSocietes && (
        <div className="h-6 w-px bg-gray-300 dark:bg-gray-600" />
      )}

      {/* Selecteur Societe */}
      {hasMultipleSocietes && (
        <div className="relative" ref={societeRef}>
          <button
            onClick={() => setSocieteDropdownOpen(!societeDropdownOpen)}
            disabled={loading}
            className={`
              flex items-center gap-2 px-3 py-1.5 rounded-lg
              ${selectedSociete
                ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-700'
                : 'bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-700'
              }
              border hover:bg-opacity-80 cursor-pointer
              transition-colors text-sm
            `}
          >
            <Filter size={14} />
            <span className="max-w-[120px] truncate">
              {selectedSociete
                ? societesList.find(s => (s.code_societe || s.societe_code) === selectedSociete)?.nom_societe || selectedSociete
                : 'Toutes societes'
              }
            </span>
            <ChevronDown
              size={14}
              className={`transition-transform ${societeDropdownOpen ? 'rotate-180' : ''}`}
            />
          </button>

          {/* Bouton reset filtre */}
          {selectedSociete && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleSocieteChange(null);
              }}
              className="absolute -right-2 -top-2 p-0.5 bg-red-100 dark:bg-red-900/50 text-red-600 dark:text-red-400 rounded-full hover:bg-red-200 dark:hover:bg-red-900"
            >
              <X size={12} />
            </button>
          )}

          {/* Dropdown Societes */}
          {societeDropdownOpen && (
            <div className="absolute top-full left-0 mt-1 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50 overflow-hidden">
              <div className="py-1 max-h-64 overflow-y-auto">
                {/* Option Toutes */}
                <button
                  onClick={() => handleSocieteChange(null)}
                  className={`
                    w-full px-4 py-2 text-left flex items-center justify-between
                    hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors
                    ${!selectedSociete ? 'bg-blue-50 dark:bg-blue-900/30' : ''}
                  `}
                >
                  <div className="flex items-center gap-2">
                    <Store size={16} className="text-gray-400" />
                    <span className="font-medium text-sm text-gray-900 dark:text-white">
                      Toutes les societes
                    </span>
                  </div>
                  {!selectedSociete && (
                    <Check size={16} className="text-blue-600" />
                  )}
                </button>

                <div className="border-t border-gray-100 dark:border-gray-700 my-1" />

                {/* Liste des societes */}
                {societesList.map((societe) => {
                  const code = societe.code_societe || societe.societe_code;
                  const nom = societe.nom_societe;
                  const isSelected = selectedSociete === code;

                  return (
                    <button
                      key={code}
                      onClick={() => handleSocieteChange(code)}
                      className={`
                        w-full px-4 py-2 text-left flex items-center justify-between
                        hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors
                        ${isSelected ? 'bg-blue-50 dark:bg-blue-900/30' : ''}
                      `}
                    >
                      <div className="flex items-center gap-2">
                        <Store size={16} className="text-gray-400" />
                        <div>
                          <div className="font-medium text-sm text-gray-900 dark:text-white">
                            {nom}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {code}
                          </div>
                        </div>
                      </div>
                      {isSelected && (
                        <Check size={16} className="text-blue-600" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Indicateur de chargement */}
      {loading && (
        <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary-600 border-t-transparent" />
      )}
    </div>
  );
};

export default DWHSelector;
