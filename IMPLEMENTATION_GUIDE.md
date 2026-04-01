# FinAnnee — Guide d'Implémentation Complet
> Basé sur l'architecture OptiBoard (`D:\new projects\OptiBoard`)
> Date : 2026-03-27

---

## Table des Matières

1. [Vue d'Ensemble](#1-vue-densemble)
2. [Stack Technologique](#2-stack-technologique)
3. [Structure des Projets](#3-structure-des-projets)
4. [Base de Données — Schéma Complet](#4-base-de-données--schéma-complet)
5. [Couche Core — Modèles & Enums](#5-couche-core--modèles--enums)
6. [Couche Data — Repositories & DbContext](#6-couche-data--repositories--dbcontext)
7. [Couche Application — Services](#7-couche-application--services)
8. [Couche Présentation — Blazor Components](#8-couche-présentation--blazor-components)
9. [Authentification & Autorisation](#9-authentification--autorisation)
10. [Menus Dynamiques (BarItem)](#10-menus-dynamiques-baritem)
11. [Composants de Visualisation](#11-composants-de-visualisation)
12. [Synchronisation des Données](#12-synchronisation-des-données)
13. [Intégration Sage (Registre Windows)](#13-intégration-sage-registre-windows)
14. [Configuration appsettings.json](#14-configuration-appsettingsjson)
15. [Sécurité](#15-sécurité)
16. [Déploiement](#16-déploiement)
17. [Plan de Développement par Phases](#17-plan-de-développement-par-phases)
18. [Checklist Complète des Fichiers](#18-checklist-complète-des-fichiers)

---

## 1. Vue d'Ensemble

**FinAnnee** est une application de Business Intelligence et de gestion multi-entreprises, calquée sur **OptiBoard**. Elle permet :

- La visualisation de données SQL Server sous forme de **Grilles**, **Tableaux Croisés**, **Dashboards**, **Excel** et **Rapports PDF**
- La gestion de **connexions multiples** vers différentes bases SQL Server d'entreprise
- La **synchronisation automatique** de données entre bases (Production → BI)
- Un système de **droits granulaires** (par utilisateur, groupe, menu, colonne)
- Une **intégration Sage** via la base de registre Windows

### Différence avec OptiBoard Desktop

| OptiBoard Desktop | FinAnnee Web |
|------------------|--------------|
| .NET Framework 4.7.2 WinForms | .NET 9.0 ASP.NET Core Blazor Server |
| DevExpress 21.2 (licence payante) | MudBlazor 8.x (MIT, gratuit) |
| DevExpress Charts | ApexCharts.Blazor (MIT) |
| DevExpress XtraReports | QuestPDF 2025.x (MIT) |
| DevExpress Spreadsheet | EPPlus 8.x |
| ADO.NET + CLR SQL | Entity Framework Core 9.0 |
| Authentification custom | ASP.NET Core Identity |

---

## 2. Stack Technologique

### Packages NuGet Requis

#### FinAnnee.Core (.NET 9.0 Class Library)
```xml
<!-- Aucun package externe — modèles purs -->
```

#### FinAnnee.Data (.NET 9.0 Class Library)
```xml
<PackageReference Include="Microsoft.EntityFrameworkCore" Version="9.0.*" />
<PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" Version="9.0.*" />
<PackageReference Include="Microsoft.EntityFrameworkCore.Tools" Version="9.0.*" />
<PackageReference Include="Microsoft.AspNetCore.Identity.EntityFrameworkCore" Version="9.0.*" />
```

#### FinAnnee.BlazorApp (.NET 9.0 ASP.NET Core)
```xml
<PackageReference Include="MudBlazor" Version="8.15.*" />
<PackageReference Include="ApexCharts" Version="*" />
<PackageReference Include="QuestPDF" Version="2025.*" />
<PackageReference Include="EPPlus" Version="8.4.*" />
<PackageReference Include="Blazored.Toast" Version="*" />
<PackageReference Include="Blazored.Modal" Version="*" />
<PackageReference Include="Microsoft.AspNetCore.Identity.UI" Version="9.0.*" />
<PackageReference Include="System.Data.SqlClient" Version="4.*" />
```

#### FinAnnee.SyncService (.NET Framework 4.7.2 ou .NET 9 Worker Service)
```xml
<PackageReference Include="Topshelf" Version="4.*" />
<!-- ou pour Worker Service .NET 9 -->
<PackageReference Include="Microsoft.Extensions.Hosting" Version="9.0.*" />
```

---

## 3. Structure des Projets

```
D:\FinAnnee\
│
├── FinAnnee.sln                        # Solution principale
│
├── FinAnnee.Core/                      # Modèles et enums partagés
│   ├── FinAnnee.Core.csproj            # <TargetFramework>net9.0</TargetFramework>
│   ├── Models/
│   │   ├── User.cs
│   │   ├── Group.cs
│   │   ├── CompanyConnection.cs
│   │   ├── BarItem.cs
│   │   ├── SyncQuery.cs
│   │   ├── SyncQueryConnection.cs
│   │   ├── SyncQueryConnectionAppointment.cs
│   │   ├── SyncHistory.cs
│   │   ├── RightItemGroup.cs
│   │   ├── RightColumnItemGroup.cs
│   │   ├── RightConnectionUser.cs
│   │   ├── Mapping.cs
│   │   └── Setting.cs
│   └── Enums/
│       ├── BarItemType.cs
│       ├── DataSourceType.cs
│       ├── ItemDestination.cs
│       ├── SyncQueryType.cs
│       └── SourceType.cs               # Modules Sage: CIAL, CPTA, IMMO, PAIE, TRES
│
├── FinAnnee.Data/                      # Couche d'accès aux données
│   ├── FinAnnee.Data.csproj
│   ├── ApplicationDbContext.cs
│   ├── DynamicDbContext.cs             # Connexions dynamiques entreprise
│   ├── Repositories/
│   │   ├── IRepository.cs
│   │   ├── Repository.cs
│   │   ├── IUserRepository.cs
│   │   ├── UserRepository.cs
│   │   ├── IBarItemRepository.cs
│   │   ├── BarItemRepository.cs
│   │   ├── ICompanyConnectionRepository.cs
│   │   ├── CompanyConnectionRepository.cs
│   │   ├── ISyncQueryRepository.cs
│   │   └── SyncQueryRepository.cs
│   └── Migrations/                     # Générées via dotnet ef
│
├── FinAnnee.BlazorApp/                 # Application Blazor Server
│   ├── FinAnnee.BlazorApp.csproj
│   ├── Program.cs
│   ├── App.razor
│   ├── _Imports.razor
│   ├── appsettings.json
│   ├── appsettings.Development.json
│   ├── Components/
│   │   ├── Layout/
│   │   │   ├── MainLayout.razor
│   │   │   ├── MainLayout.razor.cs
│   │   │   ├── NavMenu.razor
│   │   │   └── AppBar.razor
│   │   ├── Pages/
│   │   │   ├── Home.razor
│   │   │   ├── Login.razor
│   │   │   ├── SelectConnection.razor
│   │   │   └── Error.razor
│   │   ├── Core/
│   │   │   ├── GridView/
│   │   │   │   ├── GridViewComponent.razor
│   │   │   │   ├── GridViewSettings.razor
│   │   │   │   ├── GridViewExport.razor
│   │   │   │   ├── SparkLineColumn.razor
│   │   │   │   ├── UnboundColumn.razor
│   │   │   │   └── FormatColumn.razor
│   │   │   ├── PivotGrid/
│   │   │   │   ├── PivotGridComponent.razor
│   │   │   │   ├── PivotFieldList.razor
│   │   │   │   ├── PivotFieldArea.razor
│   │   │   │   ├── PivotFieldSettings.razor
│   │   │   │   ├── PivotCalculatedField.razor
│   │   │   │   ├── PivotTopNFilter.razor
│   │   │   │   ├── PivotChartView.razor
│   │   │   │   └── PivotDrillDown.razor
│   │   │   ├── Dashboard/
│   │   │   │   ├── DashboardComponent.razor
│   │   │   │   ├── DashboardCard.razor
│   │   │   │   ├── DashboardChart.razor
│   │   │   │   ├── DashboardFilter.razor
│   │   │   │   └── DashboardSettings.razor
│   │   │   ├── Excel/
│   │   │   │   ├── ExcelComponent.razor
│   │   │   │   ├── ExcelWorksheet.razor
│   │   │   │   └── ExcelExport.razor
│   │   │   └── Report/
│   │   │       ├── ReportComponent.razor
│   │   │       ├── ReportViewer.razor
│   │   │       └── ReportSettings.razor
│   │   └── Management/
│   │       ├── BarItem/
│   │       │   ├── BarItemManager.razor
│   │       │   ├── BarItemForm.razor
│   │       │   ├── DataSourceEditor.razor
│   │       │   ├── QueryBuilder.razor
│   │       │   ├── QueryParameter.razor
│   │       │   ├── MappingEditor.razor
│   │       │   └── IconSelector.razor
│   │       ├── User/
│   │       │   ├── UserManager.razor
│   │       │   ├── UserForm.razor
│   │       │   ├── GroupManager.razor
│   │       │   ├── GroupForm.razor
│   │       │   ├── RightsManager.razor
│   │       │   └── ThemeSelector.razor
│   │       ├── SyncQuery/
│   │       │   ├── SyncQueryManager.razor
│   │       │   ├── SyncQueryForm.razor
│   │       │   ├── SyncScheduler.razor
│   │       │   ├── SyncServiceControl.razor
│   │       │   └── SyncHistory.razor
│   │       └── Connection/
│   │           ├── ConnectionManager.razor
│   │           ├── ConnectionForm.razor
│   │           └── ConnectionTest.razor
│   ├── Services/
│   │   ├── IAuthenticationService.cs
│   │   ├── AuthenticationService.cs
│   │   ├── IDataSourceService.cs
│   │   ├── DataSourceService.cs
│   │   ├── IExportService.cs
│   │   ├── ExportService.cs
│   │   ├── IPivotService.cs
│   │   ├── PivotService.cs
│   │   ├── ILayoutService.cs
│   │   ├── LayoutService.cs
│   │   ├── IThemeService.cs
│   │   └── ThemeService.cs
│   ├── Helpers/
│   │   ├── QueryHelper.cs
│   │   ├── MappingHelper.cs
│   │   ├── ExpressionEvaluator.cs
│   │   ├── DataTableHelper.cs
│   │   └── EncryptionHelper.cs
│   └── wwwroot/
│       ├── css/
│       │   ├── app.css
│       │   └── mudblazor-custom.css
│       ├── js/
│       │   ├── interop.js
│       │   └── apexcharts-interop.js
│       └── favicon.ico
│
└── FinAnnee.SyncService/               # Service Windows de synchronisation
    ├── FinAnnee.SyncService.csproj
    ├── Program.cs
    ├── Service.cs
    └── App.config
```

---

## 4. Base de Données — Schéma Complet

### Base principale : `FinAnnee`

```sql
-- ============================================================
-- AUTHENTIFICATION (ASP.NET Core Identity)
-- ============================================================

CREATE TABLE [Group] (
    Id          INT IDENTITY(1,1) PRIMARY KEY,
    Caption     NVARCHAR(200)   NOT NULL,
    Description NVARCHAR(500)   NULL
);

CREATE TABLE [User] (
    Id           NVARCHAR(450)  PRIMARY KEY,   -- Identity GUID
    UserName     NVARCHAR(256)  NOT NULL,
    PasswordHash NVARCHAR(MAX)  NOT NULL,       -- PBKDF2 via Identity
    Email        NVARCHAR(256)  NULL,
    Avatar       VARBINARY(MAX) NULL,           -- Photo utilisateur (PNG)
    Status       NVARCHAR(50)   NULL,
    Theme        NVARCHAR(100)  NULL,           -- Nom du thème MudBlazor
    GroupId      INT            NOT NULL REFERENCES [Group](Id)
    -- + toutes les colonnes ASP.NET Identity standard
);

-- ============================================================
-- CONNEXIONS ENTREPRISE
-- ============================================================

CREATE TABLE CompanyConnection (
    Id             INT IDENTITY(1,1) PRIMARY KEY,
    Caption        NVARCHAR(200)   NOT NULL,
    Logo           VARBINARY(MAX)  NULL,        -- Logo PNG entreprise
    LogoPrintingSize INT           DEFAULT 100,
    LocalAddress   NVARCHAR(300)   NOT NULL,    -- Serveur SQL local
    ForeignAddress NVARCHAR(300)   NULL,        -- Serveur SQL distant (failover)
    [Database]     NVARCHAR(200)   NOT NULL,
    [User]         NVARCHAR(100)   NULL,        -- NULL = Windows Auth
    Password       NVARCHAR(500)   NULL,        -- Chiffré AES-256
    ForeignServer  NVARCHAR(MAX)   NULL,        -- JSON MsSqlConnectionString BI distant
    HasDevDb       BIT             DEFAULT 0,
    [Default]      BIT             DEFAULT 0
);

-- ============================================================
-- MENUS DYNAMIQUES
-- ============================================================

CREATE TABLE BarItem (
    Id                   INT IDENTITY(1,1) PRIMARY KEY,
    Caption              NVARCHAR(300)   NOT NULL,
    Icon                 VARBINARY(MAX)  NULL,        -- Icône PNG
    [Type]               INT             NOT NULL,    -- BarItemType enum
    DsType               INT             DEFAULT 0,   -- DataSourceType enum
    Destination          INT             DEFAULT 2,   -- ItemDestination: Desktop=0,Web=1,All=2
    SageType             INT             DEFAULT 0,   -- SourceType: CIAL,CPTA,IMMO,PAIE,TRES
    BeginGroup           BIT             DEFAULT 0,
    Visible              BIT             DEFAULT 1,
    Modal                BIT             DEFAULT 0,
    DataSource           VARBINARY(MAX)  NULL,        -- XML SqlDataSource (requêtes SQL)
    [File]               VARBINARY(MAX)  NULL,        -- .xml (dashboard) / .xlsx / .repx
    PrintSettings        VARBINARY(MAX)  NULL,        -- Paramètres impression
    PageHeaderFooter     VARBINARY(MAX)  NULL,        -- En-tête/pied de page
    GridViewMaxColumn    INT             DEFAULT 50,
    [Rank]               INT             DEFAULT 0,   -- Ordre d'affichage
    HasChildren          BIT             DEFAULT 0,
    ParentId             INT             NULL REFERENCES BarItem(Id),
    CompanyConnectionId  INT             NOT NULL REFERENCES CompanyConnection(Id)
);

-- ============================================================
-- DROITS
-- ============================================================

CREATE TABLE RightItemGroup (
    Id        INT IDENTITY(1,1) PRIMARY KEY,
    BarItemId INT NOT NULL REFERENCES BarItem(Id) ON DELETE CASCADE,
    GroupId   INT NOT NULL REFERENCES [Group](Id) ON DELETE CASCADE,
    UNIQUE (BarItemId, GroupId)
);

CREATE TABLE RightColumnItemGroup (
    Id              INT IDENTITY(1,1) PRIMARY KEY,
    BarItemId       INT           NOT NULL REFERENCES BarItem(Id) ON DELETE CASCADE,
    GroupId         INT           NOT NULL REFERENCES [Group](Id) ON DELETE CASCADE,
    ExcludedColumns NVARCHAR(MAX) NULL    -- Noms colonnes séparés par virgule
);

CREATE TABLE RightConnectionUser (
    Id                  INT IDENTITY(1,1) PRIMARY KEY,
    CompanyConnectionId INT           NOT NULL REFERENCES CompanyConnection(Id) ON DELETE CASCADE,
    UserId              NVARCHAR(450) NOT NULL REFERENCES [User](Id) ON DELETE CASCADE,
    UNIQUE (CompanyConnectionId, UserId)
);

-- ============================================================
-- SYNCHRONISATION
-- ============================================================

CREATE TABLE SyncQuery (
    Id           INT IDENTITY(1,1) PRIMARY KEY,
    Caption      NVARCHAR(300)   NOT NULL,
    Activated    BIT             DEFAULT 1,
    Editable     BIT             DEFAULT 1,
    Encrypted    BIT             DEFAULT 0,
    [Order]      INT             DEFAULT 0,
    [Type]       INT             NOT NULL,    -- SyncQueryType: NormalSync=0, RealSync=1
    DestTable    NVARCHAR(300)   NULL,        -- Table destination dans BI_Database
    SrcTable     NVARCHAR(300)   NULL,        -- Info libre / table source
    Query        NVARCHAR(MAX)   NOT NULL     -- SQL (RealSync: champs#|#FROM clause)
);

CREATE TABLE SyncQueryConnection (
    Id                  INT IDENTITY(1,1) PRIMARY KEY,
    SyncQueryId         INT NOT NULL REFERENCES SyncQuery(Id) ON DELETE CASCADE,
    CompanyConnectionId INT NOT NULL REFERENCES CompanyConnection(Id) ON DELETE CASCADE,
    [Order]             INT DEFAULT 0
);

CREATE TABLE SyncQueryConnectionAppointment (
    Id                    INT IDENTITY(1,1) PRIMARY KEY,
    SyncQueryConnectionId INT           NOT NULL REFERENCES SyncQueryConnection(Id) ON DELETE CASCADE,
    StartDate             DATETIME2     NOT NULL,
    EndDate               DATETIME2     NULL,
    RecurrenceInfo        NVARCHAR(MAX) NULL    -- JSON récurrence (Daily/Weekly/Monthly)
);

CREATE TABLE SyncHistory (
    Id                    INT IDENTITY(1,1) PRIMARY KEY,
    SyncQueryConnectionId INT           NOT NULL REFERENCES SyncQueryConnection(Id),
    ExecutionDate         DATETIME2     NOT NULL DEFAULT GETUTCDATE(),
    Status                NVARCHAR(50)  NOT NULL,    -- Success / Error / Running
    RowsAffected          INT           NULL,
    DurationMs            INT           NULL,
    ErrorMessage          NVARCHAR(MAX) NULL
);

-- ============================================================
-- PARAMÈTRES & MAPPING
-- ============================================================

CREATE TABLE Setting (
    Id          INT IDENTITY(1,1) PRIMARY KEY,
    UserId      NVARCHAR(450) NOT NULL REFERENCES [User](Id) ON DELETE CASCADE,
    BarItemId   INT           NOT NULL REFERENCES BarItem(Id) ON DELETE CASCADE,
    SettingType NVARCHAR(100) NOT NULL,    -- GridLayout / PivotLayout / etc.
    [Value]     NVARCHAR(MAX) NULL         -- XML ou JSON layout sauvegardé
);

CREATE TABLE Mapping (
    Id            INT IDENTITY(1,1) PRIMARY KEY,
    BarItemId     INT           NOT NULL REFERENCES BarItem(Id) ON DELETE CASCADE,
    FieldName     NVARCHAR(300) NOT NULL,
    DisplayFolder NVARCHAR(300) NULL    -- Ex: "Product\Category"
);
```

---

## 5. Couche Core — Modèles & Enums

### 5.1 Enums (FinAnnee.Core/Enums/)

#### BarItemType.cs
```csharp
namespace FinAnnee.Core.Enums;

public enum BarItemType
{
    Nothing  = -1,   // Dossier menu (pas de composant)
    GridView  = 0,   // Grille de données (requiert DataSource)
    PivotGrid = 1,   // Tableau croisé dynamique (requiert DataSource)
    Report    = 2,   // Rapport PDF (requiert File .repx ou config)
    Dashboard = 3,   // Tableau de bord (requiert File .xml config)
    Excel     = 4    // Feuilles Excel (requiert DataSource)
}
```

#### DataSourceType.cs
```csharp
namespace FinAnnee.Core.Enums;

/// <summary>
/// 15 combinaisons de fallback entre sources Normal / BI Local / BI Distant
/// </summary>
public enum DataSourceType
{
    None                                             = -1,
    Normal                                           = 0,   // Base production
    LocalSynchronizing                               = 1,   // BI_NomBase
    ForeignSynchronizing                             = 2,   // Serveur BI distant
    NormalThenLocalSynchronizing                     = 3,
    NormalThenForeignSynchronizing                   = 4,
    NormalThenLocalSynchronizingThenForeignSynchronizing  = 5,
    NormalThenForeignSynchronizingThenLocalSynchronizing  = 6,
    LocalSynchronizingThenNormal                     = 7,
    LocalSynchronizingThenForeignSynchronizing        = 8,
    LocalSynchronizingThenNormalThenForeignSynchronizing  = 9,
    LocalSynchronizingThenForeignSynchronizingThenNormal  = 10,
    ForeignSynchronizingThenNormal                   = 11,
    ForeignSynchronizingThenLocalSynchronizing        = 12,
    ForeignSynchronizingThenNormalThenLocalSynchronizing  = 13,
    ForeignSynchronizingThenLocalSynchronizingThenNormal  = 14
}
```

#### ItemDestination.cs
```csharp
namespace FinAnnee.Core.Enums;

public enum ItemDestination
{
    None    = -1,
    Desktop =  0,
    Web     =  1,
    All     =  2
}
```

#### SyncQueryType.cs
```csharp
namespace FinAnnee.Core.Enums;

public enum SyncQueryType
{
    NormalSync = 0,   // DROP TABLE + SELECT INTO (recréation complète)
    RealSync   = 1    // MERGE (UPDATE/INSERT/DELETE)
}
```

#### SourceType.cs (Modules Sage)
```csharp
namespace FinAnnee.Core.Enums;

public enum SourceType
{
    CIAL = 0,   // Gestion Commerciale
    CPTA = 1,   // Comptabilité
    IMMO = 2,   // Immobilisations
    PAIE = 3,   // Paie
    TRES = 4    // Trésorerie
}
```

### 5.2 Modèles (FinAnnee.Core/Models/)

#### CompanyConnection.cs
```csharp
namespace FinAnnee.Core.Models;

public class CompanyConnection
{
    public int    Id             { get; set; }
    public string Caption        { get; set; } = null!;
    public byte[] Logo           { get; set; }
    public int    LogoPrintingSize { get; set; } = 100;
    public string LocalAddress   { get; set; } = null!;
    public string ForeignAddress { get; set; }
    public string Database       { get; set; } = null!;
    public string User           { get; set; }           // null = Windows Auth
    public string Password       { get; set; }           // Chiffré AES-256
    public string ForeignServer  { get; set; }           // JSON de connexion BI distant
    public bool   HasDevDb       { get; set; }
    public bool   Default        { get; set; }

    // Navigation
    public List<BarItem>              BarItems       { get; set; } = new();
    public List<SyncQueryConnection>  SyncConnections { get; set; } = new();
    public List<RightConnectionUser>  UserRights     { get; set; } = new();

    /// <summary>
    /// Résout le serveur actif (local ou distant selon disponibilité)
    /// </summary>
    public string ResolveServer(bool preferLocal = true)
        => preferLocal ? (LocalAddress ?? ForeignAddress) : (ForeignAddress ?? LocalAddress);

    /// <summary>
    /// Construit la chaîne de connexion SQL Server
    /// </summary>
    public string BuildConnectionString(DataSourceType dsType = DataSourceType.Normal)
    {
        var db = dsType == DataSourceType.LocalSynchronizing
            ? (Database.StartsWith("BI_") ? Database : "BI_" + Database)
            : Database;
        var server = ResolveServer();
        return string.IsNullOrEmpty(User)
            ? $"Server={server};Database={db};Trusted_Connection=True;TrustServerCertificate=True;"
            : $"Server={server};Database={db};User Id={User};Password={Password};TrustServerCertificate=True;";
    }
}
```

#### BarItem.cs
```csharp
using FinAnnee.Core.Enums;

namespace FinAnnee.Core.Models;

public class BarItem
{
    public int            Id                  { get; set; }
    public string         Caption             { get; set; } = null!;
    public byte[]         Icon                { get; set; }
    public BarItemType    Type                { get; set; } = BarItemType.Nothing;
    public DataSourceType DsType              { get; set; } = DataSourceType.Normal;
    public ItemDestination Destination        { get; set; } = ItemDestination.All;
    public SourceType     SageType            { get; set; } = SourceType.CIAL;
    public bool           BeginGroup          { get; set; }
    public bool           Visible             { get; set; } = true;
    public bool           Modal               { get; set; }
    public byte[]         DataSource          { get; set; }   // XML requêtes SQL
    public byte[]         File                { get; set; }   // .xml/.xlsx/.repx
    public byte[]         PrintSettings       { get; set; }
    public byte[]         PageHeaderFooter    { get; set; }
    public int            GridViewMaxColumn   { get; set; } = 50;
    public int            Rank                { get; set; }
    public bool           HasChildren         { get; set; }

    // Foreign Keys
    public int?           ParentId            { get; set; }
    public int            CompanyConnectionId { get; set; }

    // Navigation
    public BarItem              Parent     { get; set; }
    public List<BarItem>        Children   { get; set; } = new();
    public CompanyConnection    Connection { get; set; }
    public List<RightItemGroup> Rights     { get; set; } = new();
    public List<Mapping>        Mappings   { get; set; } = new();

    public bool HasControl() => Type != BarItemType.Nothing;
    public bool HasFile()    => File != null && File.Length > 0;
}
```

#### SyncQuery.cs
```csharp
using FinAnnee.Core.Enums;

namespace FinAnnee.Core.Models;

public class SyncQuery
{
    public int           Id            { get; set; }
    public string        Caption       { get; set; } = null!;
    public bool          Activated     { get; set; } = true;
    public bool          Editable      { get; set; } = true;
    public bool          Encrypted     { get; set; }
    public int           Order         { get; set; }
    public SyncQueryType Type          { get; set; }
    public string        DestTable     { get; set; }   // Table cible BI
    public string        SrcTable      { get; set; }   // Info libre
    public string        Query         { get; set; }   // SQL brut

    // RealSync: "champs #|# FROM clause"
    public static readonly string[] Separator = { "#|#" };

    public string FieldsClause => Type == SyncQueryType.RealSync
        ? Query.Split(Separator, StringSplitOptions.RemoveEmptyEntries)[0].Trim()
        : Query;

    public string FromClause => Type == SyncQueryType.RealSync
        ? Query.Split(Separator, StringSplitOptions.RemoveEmptyEntries)[1].Trim()
        : Query;

    // Navigation
    public List<SyncQueryConnection> Connections { get; set; } = new();
}
```

---

## 6. Couche Data — Repositories & DbContext

### 6.1 ApplicationDbContext.cs

```csharp
using FinAnnee.Core.Models;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;

namespace FinAnnee.Data;

public class ApplicationDbContext : IdentityDbContext<User>
{
    public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
        : base(options) { }

    public DbSet<Group>                           Groups                           { get; set; }
    public DbSet<CompanyConnection>               CompanyConnections               { get; set; }
    public DbSet<BarItem>                         BarItems                         { get; set; }
    public DbSet<RightItemGroup>                  RightItemGroups                  { get; set; }
    public DbSet<RightColumnItemGroup>            RightColumnItemGroups            { get; set; }
    public DbSet<RightConnectionUser>             RightConnectionUsers             { get; set; }
    public DbSet<SyncQuery>                       SyncQueries                      { get; set; }
    public DbSet<SyncQueryConnection>             SyncQueryConnections             { get; set; }
    public DbSet<SyncQueryConnectionAppointment>  SyncQueryConnectionAppointments  { get; set; }
    public DbSet<SyncHistory>                     SyncHistories                    { get; set; }
    public DbSet<Setting>                         Settings                         { get; set; }
    public DbSet<Mapping>                         Mappings                         { get; set; }

    protected override void OnModelCreating(ModelBuilder builder)
    {
        base.OnModelCreating(builder);

        // BarItem auto-référence
        builder.Entity<BarItem>()
            .HasOne(b => b.Parent)
            .WithMany(b => b.Children)
            .HasForeignKey(b => b.ParentId)
            .OnDelete(DeleteBehavior.Restrict);

        // CompanyConnection cascade
        builder.Entity<BarItem>()
            .HasOne(b => b.Connection)
            .WithMany(c => c.BarItems)
            .HasForeignKey(b => b.CompanyConnectionId)
            .OnDelete(DeleteBehavior.Cascade);

        // Unicité droits
        builder.Entity<RightItemGroup>()
            .HasIndex(r => new { r.BarItemId, r.GroupId }).IsUnique();
        builder.Entity<RightConnectionUser>()
            .HasIndex(r => new { r.CompanyConnectionId, r.UserId }).IsUnique();
    }
}
```

### 6.2 Pattern Repository Générique

```csharp
// IRepository.cs
namespace FinAnnee.Data.Repositories;

public interface IRepository<T> where T : class
{
    Task<T?>               GetByIdAsync(object id);
    Task<IEnumerable<T>>   GetAllAsync();
    Task<IEnumerable<T>>   FindAsync(Expression<Func<T, bool>> predicate);
    Task                   AddAsync(T entity);
    Task                   UpdateAsync(T entity);
    Task                   DeleteAsync(object id);
    Task<int>              SaveChangesAsync();
}

// Repository.cs
public class Repository<T> : IRepository<T> where T : class
{
    protected readonly ApplicationDbContext _context;
    protected readonly DbSet<T> _dbSet;

    public Repository(ApplicationDbContext context)
    {
        _context = context;
        _dbSet   = context.Set<T>();
    }

    public async Task<T?> GetByIdAsync(object id)
        => await _dbSet.FindAsync(id);

    public async Task<IEnumerable<T>> GetAllAsync()
        => await _dbSet.ToListAsync();

    public async Task<IEnumerable<T>> FindAsync(Expression<Func<T, bool>> predicate)
        => await _dbSet.Where(predicate).ToListAsync();

    public async Task AddAsync(T entity)
        => await _dbSet.AddAsync(entity);

    public async Task UpdateAsync(T entity)
        => _context.Entry(entity).State = EntityState.Modified;

    public async Task DeleteAsync(object id)
    {
        var entity = await GetByIdAsync(id);
        if (entity != null) _dbSet.Remove(entity);
    }

    public async Task<int> SaveChangesAsync()
        => await _context.SaveChangesAsync();
}
```

### 6.3 BarItemRepository (exemple spécialisé)

```csharp
public interface IBarItemRepository : IRepository<BarItem>
{
    Task<IEnumerable<BarItem>> GetRootItemsAsync(int connectionId, int? groupId = null);
    Task<IEnumerable<BarItem>> GetChildrenAsync(int parentId, int? groupId = null);
    Task UpdateHasChildrenAsync();
}

public class BarItemRepository : Repository<BarItem>, IBarItemRepository
{
    public BarItemRepository(ApplicationDbContext context) : base(context) { }

    public async Task<IEnumerable<BarItem>> GetRootItemsAsync(int connectionId, int? groupId = null)
    {
        var query = _dbSet
            .Where(b => b.CompanyConnectionId == connectionId
                     && b.ParentId == null
                     && b.Visible
                     && b.Destination != ItemDestination.Desktop);

        if (groupId.HasValue)
            query = query.Where(b => b.Rights.Any(r => r.GroupId == groupId));

        return await query.OrderBy(b => b.Rank).ToListAsync();
    }

    public async Task<IEnumerable<BarItem>> GetChildrenAsync(int parentId, int? groupId = null)
    {
        var query = _dbSet
            .Where(b => b.ParentId == parentId && b.Visible);

        if (groupId.HasValue)
            query = query.Where(b => b.Rights.Any(r => r.GroupId == groupId));

        return await query.OrderBy(b => b.Rank).ToListAsync();
    }

    public async Task UpdateHasChildrenAsync()
    {
        // Mise à jour du flag HasChildren pour tous les items
        var items = await _dbSet.ToListAsync();
        foreach (var item in items)
            item.HasChildren = items.Any(b => b.ParentId == item.Id);
        await _context.SaveChangesAsync();
    }
}
```

---

## 7. Couche Application — Services

### 7.1 IDataSourceService.cs

```csharp
namespace FinAnnee.BlazorApp.Services;

public interface IDataSourceService
{
    /// <summary>Exécute un SELECT et retourne un DataTable</summary>
    Task<DataTable> ExecuteQueryAsync(
        string connectionString,
        string query,
        Dictionary<string, object>? parameters = null);

    /// <summary>Exécute une procédure stockée</summary>
    Task<DataTable> ExecuteStoredProcedureAsync(
        string connectionString,
        string procName,
        Dictionary<string, object>? parameters = null);

    /// <summary>Teste la connexion SQL Server</summary>
    Task<bool> TestConnectionAsync(string connectionString);

    /// <summary>Liste les procédures stockées disponibles</summary>
    Task<List<string>> GetStoredProceduresAsync(string connectionString);

    /// <summary>Exécute plusieurs requêtes (multi-feuilles Excel)</summary>
    Task<List<(string Name, DataTable Data)>> ExecuteMultiQueryAsync(
        string connectionString,
        List<(string Name, string Query)> queries);
}
```

### 7.2 IExportService.cs

```csharp
namespace FinAnnee.BlazorApp.Services;

public interface IExportService
{
    Task<byte[]> ExportToPdfAsync(ExportPdfConfig config);
    Task<byte[]> ExportToExcelAsync(DataTable data, ExportExcelConfig config);
    Task<byte[]> ExportPivotToExcelAsync(PivotTable pivot, string sheetName = "Pivot");
    Task<byte[]> ExportMultiSheetExcelAsync(List<(string Name, DataTable Data)> sheets);
}

public class ExportPdfConfig
{
    public string          Title      { get; set; } = "Rapport";
    public DataTable       Data       { get; set; }
    public byte[]          Logo       { get; set; }
    public bool            ShowHeader { get; set; } = true;
    public bool            ShowFooter { get; set; } = true;
    public string          FooterText { get; set; }
    public List<string>    ExcludedColumns { get; set; } = new();
}

public class ExportExcelConfig
{
    public string       SheetName  { get; set; } = "Données";
    public bool         AutoFilter { get; set; } = true;
    public bool         FreezeRow  { get; set; } = true;
    public List<string> ExcludedColumns { get; set; } = new();
}
```

### 7.3 IPivotService.cs

```csharp
namespace FinAnnee.BlazorApp.Services;

public interface IPivotService
{
    Task<PivotTable> BuildAsync(DataTable source, PivotConfiguration config);
    Task<DataTable>  DrillDownAsync(PivotTable pivot, PivotCell cell);
}

public class PivotConfiguration
{
    public List<string>      RowFields    { get; set; } = new();
    public List<string>      ColumnFields { get; set; } = new();
    public List<ValueField>  ValueFields  { get; set; } = new();
    public List<string>      FilterFields { get; set; } = new();
    public int?              TopN         { get; set; }
}

public class ValueField
{
    public string            Name      { get; set; }
    public AggregateFunction Aggregate { get; set; } = AggregateFunction.Sum;
    public string            Format    { get; set; } = "N2";
}

public enum AggregateFunction { Sum, Average, Count, Min, Max }
```

### 7.4 IAuthenticationService.cs

```csharp
namespace FinAnnee.BlazorApp.Services;

public interface IAuthenticationService
{
    Task<(bool Success, string Error)> LoginAsync(
        string username, string password, CompanyConnection connection);
    Task LogoutAsync();
    Task<User?> GetCurrentUserAsync();
    bool IsAuthenticated();
    bool IsAdmin();
    bool IsSuperAdmin();
    Task<List<CompanyConnection>> GetAllowedConnectionsAsync();
}
```

---

## 8. Couche Présentation — Blazor Components

### 8.1 Program.cs

```csharp
using FinAnnee.Data;
using FinAnnee.BlazorApp.Services;
using Microsoft.EntityFrameworkCore;
using MudBlazor.Services;

var builder = WebApplication.CreateBuilder(args);

// Blazor Server
builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents();

// MudBlazor
builder.Services.AddMudServices();

// Entity Framework
builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseSqlServer(
        builder.Configuration.GetConnectionString("DefaultConnection"),
        b => b.MigrationsAssembly("FinAnnee.Data")));

// ASP.NET Core Identity
builder.Services.AddIdentity<User, IdentityRole>(options =>
{
    options.Password.RequireDigit           = false;
    options.Password.RequiredLength         = 4;
    options.Password.RequireNonAlphanumeric = false;
    options.Password.RequireUppercase       = false;
})
.AddEntityFrameworkStores<ApplicationDbContext>();

// Repositories
builder.Services.AddScoped(typeof(IRepository<>), typeof(Repository<>));
builder.Services.AddScoped<IBarItemRepository, BarItemRepository>();
builder.Services.AddScoped<ICompanyConnectionRepository, CompanyConnectionRepository>();
builder.Services.AddScoped<ISyncQueryRepository, SyncQueryRepository>();

// Services
builder.Services.AddScoped<IAuthenticationService, AuthenticationService>();
builder.Services.AddScoped<IDataSourceService, DataSourceService>();
builder.Services.AddScoped<IExportService, ExportService>();
builder.Services.AddScoped<IPivotService, PivotService>();
builder.Services.AddScoped<ILayoutService, LayoutService>();
builder.Services.AddScoped<IThemeService, ThemeService>();

// Session
builder.Services.AddSession(options =>
{
    options.IdleTimeout        = TimeSpan.FromHours(8);
    options.Cookie.HttpOnly    = true;
    options.Cookie.IsEssential = true;
});
builder.Services.AddHttpContextAccessor();

// Localisation fr-FR
builder.Services.AddLocalization();

var app = builder.Build();

app.UseSession();
app.UseAuthentication();
app.UseAuthorization();
app.MapRazorComponents<App>()
   .AddInteractiveServerRenderMode();

app.Run();
```

### 8.2 MainLayout.razor (structure)

```razor
@inherits LayoutComponentBase
@inject IAuthenticationService AuthService
@inject NavigationManager Nav

<MudLayout>
    <!-- Barre d'application -->
    <MudAppBar Elevation="1">
        <MudIconButton Icon="@Icons.Material.Filled.Menu"
                       Color="Color.Inherit"
                       Edge="Edge.Start"
                       OnClick="ToggleDrawer" />
        <MudText Typo="Typo.h6">FinAnnee</MudText>
        <MudSpacer />
        <!-- Utilisateur connecté + déconnexion -->
        <MudText>@_currentUser?.UserName</MudText>
        <MudIconButton Icon="@Icons.Material.Filled.Logout"
                       OnClick="Logout" />
    </MudAppBar>

    <!-- Menu latéral dynamique -->
    <MudDrawer @bind-Open="_drawerOpen" Elevation="2">
        <NavMenu />
    </MudDrawer>

    <!-- Contenu principal -->
    <MudMainContent>
        <MudContainer MaxWidth="MaxWidth.ExtraExtraLarge">
            @Body
        </MudContainer>
    </MudMainContent>
</MudLayout>
```

### 8.3 NavMenu.razor (menus dynamiques BarItem)

```razor
@inject IBarItemRepository BarItemRepo
@inject IAuthenticationService AuthService
@inject NavigationManager Nav

<MudNavMenu>
    @foreach (var item in _rootItems)
    {
        @if (item.HasChildren)
        {
            <MudNavGroup Title="@item.Caption" Icon="@GetIcon(item)">
                @* Chargement lazy des enfants *@
                <ChildContent>
                    @foreach (var child in GetChildren(item.Id))
                    {
                        <MudNavLink Href="@GetRoute(child)">
                            @child.Caption
                        </MudNavLink>
                    }
                </ChildContent>
            </MudNavGroup>
        }
        else if (item.HasControl())
        {
            <MudNavLink Href="@GetRoute(item)" Icon="@GetIcon(item)">
                @item.Caption
            </MudNavLink>
        }
    }
</MudNavMenu>

@code {
    private List<BarItem> _rootItems = new();

    protected override async Task OnInitializedAsync()
    {
        var user = await AuthService.GetCurrentUserAsync();
        var groupId = AuthService.IsAdmin() ? (int?)null : user?.GroupId;
        _rootItems = (await BarItemRepo.GetRootItemsAsync(
            CompanyConnection.CurrentId, groupId)).ToList();
    }

    private string GetRoute(BarItem item) => item.Type switch
    {
        BarItemType.GridView  => $"/gridview/{item.Id}",
        BarItemType.PivotGrid => $"/pivotgrid/{item.Id}",
        BarItemType.Dashboard => $"/dashboard/{item.Id}",
        BarItemType.Excel     => $"/excel/{item.Id}",
        BarItemType.Report    => $"/report/{item.Id}",
        _                     => "#"
    };
}
```

---

## 9. Authentification & Autorisation

### Flux complet

```
[Login.razor]
    ↓ username + password + CompanyConnection sélectionnée
[AuthenticationService.LoginAsync()]
    ↓ UserManager.FindByNameAsync() + PasswordHasher.VerifyPassword()
    ↓ SignInManager.SignInAsync()
    ↓ Stocker User.Current + CompanyConnection.Current en session
[SelectConnection.razor]   (si plusieurs connexions autorisées)
    ↓ RightConnectionUser → connexions autorisées pour cet user
[MainLayout.razor]
    ↓ Charger BarItems filtrés par groupe → NavMenu
```

### Niveaux d'accès

| Niveau | Condition | Accès |
|--------|-----------|-------|
| **SuperAdmin** | UserName = "ADMINISTRATOR" ET groupe "Administrateurs" | Tout + CLR SQL |
| **Admin** | Groupe "Administrateurs" (autre user) | Gestion users/menus/connexions |
| **User** | Tout autre groupe | Menus RightItemGroup + colonnes RightColumnItemGroup |

### Données initiales à insérer (seed)

```sql
-- Groupe admin
INSERT INTO [Group] (Caption) VALUES ('Administrateurs');

-- User SuperAdmin (mot de passe hashé via Identity)
-- À faire via UserManager dans le code au premier démarrage
-- UserName = 'ADMINISTRATOR', GroupId = 1

-- Connexion locale par défaut
INSERT INTO CompanyConnection (Caption, LocalAddress, [Database], [Default])
VALUES ('FinAnnee Local', 'localhost', 'FinAnnee_Prod', 1);
```

---

## 10. Menus Dynamiques (BarItem)

### Logique de résolution DataSource

```csharp
public string ResolveConnectionString(BarItem item)
{
    var conn = item.Connection;

    return item.DsType switch
    {
        DataSourceType.Normal
            => conn.BuildConnectionString(DataSourceType.Normal),
        DataSourceType.LocalSynchronizing
            => conn.BuildConnectionString(DataSourceType.LocalSynchronizing),
        DataSourceType.NormalThenLocalSynchronizing
            => TestConn(conn.BuildConnectionString(DataSourceType.Normal))
               ? conn.BuildConnectionString(DataSourceType.Normal)
               : conn.BuildConnectionString(DataSourceType.LocalSynchronizing),
        // ... les 15 combinaisons
        _ => conn.BuildConnectionString()
    };
}
```

### Format XML DataSource

Le champ `BarItem.DataSource` contient du XML représentant les requêtes SQL :

```xml
<SqlDataSource Name="MaConnexion">
  <Queries>
    <CustomSqlQuery Name="Query1">
      <Sql>SELECT * FROM Ventes WHERE Date >= @dateDebut</Sql>
      <Parameters>
        <QueryParameter Name="dateDebut" Type="DateTime" />
      </Parameters>
    </CustomSqlQuery>
    <CustomSqlQuery Name="Query2">
      <Sql>SELECT * FROM Clients</Sql>
    </CustomSqlQuery>
  </Queries>
</SqlDataSource>
```

---

## 11. Composants de Visualisation

### 11.1 GridViewComponent.razor

**Fonctionnalités à implémenter :**

| Fonctionnalité | Composant MudBlazor | Notes |
|---------------|---------------------|-------|
| Grille de données | `MudDataGrid<T>` | Virtualisation activée |
| Tri colonnes | Natif MudDataGrid | |
| Filtrage | `FilterMode.ColumnFilterRow` | |
| Pagination | `PagerContent` | 20 lignes par défaut |
| Export Excel | `IExportService.ExportToExcelAsync` | EPPlus |
| Export PDF | `IExportService.ExportToPdfAsync` | QuestPDF |
| Colonnes SparkLine | `ApexChart` inline | Mini-graphiques |
| Drill-down PivotGrid | Navigation vers `/pivotgrid/{id}` | |
| Sauvegarde layout | `ILayoutService` → Setting table | XML état |
| Colonnes exclues | `RightColumnItemGroup` | Par groupe |
| Max colonnes | `BarItem.GridViewMaxColumn` | 50 par défaut |

```razor
@page "/gridview/{ItemId:int}"
@inject IBarItemRepository BarItemRepo
@inject IDataSourceService DataSource
@inject IAuthenticationService AuthService
@inject IExportService ExportService

<MudDataGrid T="Dictionary<string,object>"
             Items="_data"
             Dense="true"
             Striped="true"
             Hover="true"
             FilterMode="DataGridFilterMode.ColumnFilterRow"
             Virtualize="true">
    <Columns>
        @foreach (var col in _columns.Where(c => !_excludedCols.Contains(c)))
        {
            <PropertyColumn Property="r => r[col]" Title="@col" />
        }
    </Columns>
    <ToolBarContent>
        <MudText Typo="Typo.h6">@_barItem?.Caption</MudText>
        <MudSpacer />
        <MudIconButton Icon="@Icons.Material.Filled.FileDownload"
                       OnClick="ExportExcel" Title="Exporter Excel" />
        <MudIconButton Icon="@Icons.Material.Filled.PictureAsPdf"
                       OnClick="ExportPdf" Title="Exporter PDF" />
    </ToolBarContent>
</MudDataGrid>
```

### 11.2 PivotGridComponent.razor

**Architecture custom (pas de librairie tierce) :**

```
PivotGridComponent.razor
├── PivotFieldList.razor         ← Champs disponibles (drag source)
├── PivotFieldArea.razor         ← Zones Rows/Columns/Values/Filters (drop targets)
├── PivotTable (rendu HTML)      ← <table> généré dynamiquement
└── PivotChartView.razor         ← ApexChart basé sur données pivot
```

**Logique de construction (PivotService.cs) :**

```csharp
public async Task<PivotTable> BuildAsync(DataTable source, PivotConfiguration config)
{
    // 1. Extraire valeurs distinctes pour colonnes
    var columnValues = source.AsEnumerable()
        .Select(r => config.ColumnFields.Select(f => r[f]?.ToString()))
        .Distinct().ToList();

    // 2. Extraire valeurs distinctes pour lignes
    var rowValues = source.AsEnumerable()
        .Select(r => config.RowFields.Select(f => r[f]?.ToString()))
        .Distinct().ToList();

    // 3. Calculer agrégats
    foreach (var row in rowValues)
        foreach (var col in columnValues)
            foreach (var val in config.ValueFields)
                pivot.Cells[row][col][val.Name] = Aggregate(source, row, col, val);

    return pivot;
}
```

### 11.3 DashboardComponent.razor

```razor
@page "/dashboard/{ItemId:int}"
@inject IDataSourceService DataSource

<MudGrid>
    <!-- Filtres date globaux -->
    <MudItem xs="12">
        <MudDateRangePicker @bind-DateRange="_dateRange"
                            Label="Période"
                            DateFormat="dd/MM/yyyy" />
        <MudButton OnClick="RefreshData" Variant="Variant.Filled">
            Actualiser
        </MudButton>
    </MudItem>

    <!-- Cartes KPI -->
    @foreach (var kpi in _kpis)
    {
        <MudItem xs="12" sm="6" md="3">
            <MudCard>
                <MudCardContent>
                    <MudText Typo="Typo.h4">@kpi.Value.ToString("N0")</MudText>
                    <MudText Typo="Typo.caption">@kpi.Label</MudText>
                </MudCardContent>
            </MudCard>
        </MudItem>
    }

    <!-- Graphiques ApexCharts -->
    @foreach (var chart in _charts)
    {
        <MudItem xs="12" md="6">
            <ApexChart TItem="ChartDataPoint"
                       Title="@chart.Title"
                       Options="_chartOptions">
                <ApexPointSeries TItem="ChartDataPoint"
                                 Items="chart.Data"
                                 Name="@chart.Series"
                                 XValue="d => d.Label"
                                 YValue="d => d.Value" />
            </ApexChart>
        </MudItem>
    }
</MudGrid>
```

### 11.4 ExcelComponent.razor

```razor
@page "/excel/{ItemId:int}"
@inject IExportService ExportService
@inject IDataSourceService DataSource

<!-- Prévisualisation feuilles -->
<MudTabs>
    @foreach (var sheet in _sheets)
    {
        <MudTabPanel Text="@sheet.Name">
            <MudDataGrid T="Dictionary<string,object>"
                         Items="sheet.Rows"
                         Dense="true" ReadOnly="true" />
        </MudTabPanel>
    }
</MudTabs>

<MudButton OnClick="DownloadExcel"
           StartIcon="@Icons.Material.Filled.Download"
           Variant="Variant.Filled" Color="Color.Success">
    Télécharger .xlsx
</MudButton>

@code {
    private async Task DownloadExcel()
    {
        var bytes = await ExportService.ExportMultiSheetExcelAsync(_sheets
            .Select(s => (s.Name, s.DataTable)).ToList());
        await JS.InvokeVoidAsync("downloadFile", $"{_barItem.Caption}.xlsx", bytes);
    }
}
```

---

## 12. Synchronisation des Données

### 12.1 Architecture SyncService

```
FinAnnee.SyncService (Worker Service .NET 9)
├── Timer 1 (700ms) → CheckAppointments()     → Déclenche syncs planifiées
├── Timer 2 (700ms) → CheckMinuteSchedules()  → Syncs par minute (modulo)
└── ExecuteSyncQuery()
    ├── NormalSync → DROP + SELECT INTO BI_Database
    └── RealSync   → MERGE (UPDATE/INSERT/DELETE)
```

### 12.2 Logique NormalSync

```sql
-- Générée automatiquement par le service
DROP TABLE IF EXISTS [BI_DatabaseName].[dbo].[DestTable]
SELECT [champs] INTO [BI_DatabaseName].[dbo].[DestTable]
FROM [SourceDatabase].[dbo].[SrcTable]
```

### 12.3 Logique RealSync

```sql
-- Query stockée au format : "VenteId,ClientId,Montant #|# FROM Production.dbo.Ventes"
-- Génère un MERGE :
MERGE [BI_Database].[dbo].[DestTable] AS target
USING (SELECT VenteId, ClientId, Montant FROM Production.dbo.Ventes) AS source
ON (target.VenteId = source.VenteId)
WHEN MATCHED THEN
    UPDATE SET ClientId = source.ClientId, Montant = source.Montant
WHEN NOT MATCHED BY TARGET THEN
    INSERT (VenteId, ClientId, Montant) VALUES (source.VenteId, source.ClientId, source.Montant)
WHEN NOT MATCHED BY SOURCE THEN
    DELETE;
```

### 12.4 Service.cs (Worker .NET 9)

```csharp
public class SyncWorker : BackgroundService
{
    private readonly IServiceProvider _services;
    private Timer _appointmentTimer;
    private Timer _minuteTimer;

    protected override Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _appointmentTimer = new Timer(CheckAppointments, null,
            TimeSpan.Zero, TimeSpan.FromMilliseconds(700));
        _minuteTimer = new Timer(CheckMinuteSchedules, null,
            TimeSpan.Zero, TimeSpan.FromMilliseconds(700));
        return Task.CompletedTask;
    }

    private async void CheckAppointments(object state)
    {
        using var scope = _services.CreateScope();
        var repo = scope.ServiceProvider.GetRequiredService<ISyncQueryRepository>();
        var due  = await repo.GetDueAppointmentsAsync(DateTime.Now);
        foreach (var appt in due)
            await ExecuteSyncAsync(appt.SyncQueryConnection);
    }
}
```

---

## 13. Intégration Sage (Registre Windows)

### Chemin registre Sage

```
HKEY_CURRENT_USER\software\Sage\{Version}\Personnalisation\
├── Menus\
│   └── {MenuGuid}\
│       ├── Caption = "FinAnnee"
│       └── Programmes externes\
│           └── {ProgGuid}\
│               ├── Chemin    = "C:\FinAnnee\FinAnnee.exe"
│               ├── Params    = "{BarItemId} {DatabaseName}"
│               ├── Contexte  = 2000
│               └── Type      = 1718185061
```

### Code d'intégration (HelperRegistry.cs)

```csharp
using Microsoft.Win32;

namespace FinAnnee.BlazorApp.Helpers;

public static class HelperRegistry
{
    private const string SageRoot = @"software\Sage";
    private const string AppName  = "FinAnnee";
    private const string AppExe   = "FinAnnee_Desktop.exe";

    /// <summary>Synchronise les menus FinAnnee dans le registre Sage</summary>
    public static void SyncSageMenus(List<BarItem> items, string sageVersion)
    {
        using var sageKey = Registry.CurrentUser.OpenSubKey(
            $@"{SageRoot}\{sageVersion}\Personnalisation",
            RegistryKeyPermissionCheck.ReadWriteSubTree);

        if (sageKey == null) return;

        foreach (var item in items.Where(i => i.SageType != SourceType.None))
        {
            var menuPath = $@"Menus\{AppName}_{item.Id}";
            using var menuKey = sageKey.CreateSubKey(menuPath);
            menuKey.SetValue("Caption", item.Caption);
            menuKey.SetValue("Visible", 1);

            // Programme externe
            using var progKey = menuKey.CreateSubKey(@"Programmes externes\001");
            progKey.SetValue("Chemin",   GetExePath());
            progKey.SetValue("Params",   $"{item.Id} {item.Connection?.Database}");
            progKey.SetValue("Contexte", 2000);
            progKey.SetValue("Type",     1718185061);
        }
    }

    /// <summary>Vérifie si un module Sage est en cours d'exécution</summary>
    public static bool IsSageRunning(SourceType module)
    {
        var moduleNames = new Dictionary<SourceType, string>
        {
            [SourceType.CIAL] = "Sage Gestion Commerciale",
            [SourceType.CPTA] = "Sage Comptabilité",
            [SourceType.IMMO] = "Sage Immobilisations",
            [SourceType.PAIE] = "Sage Paie",
            [SourceType.TRES] = "Sage Trésorerie"
        };

        return Process.GetProcesses()
            .Any(p => p.MainWindowTitle.Contains(moduleNames[module],
                StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>Détecte la version Sage installée</summary>
    public static List<string> GetInstalledSageVersions()
    {
        using var sageKey = Registry.CurrentUser.OpenSubKey(SageRoot);
        return sageKey?.GetSubKeyNames().ToList() ?? new List<string>();
    }

    private static string GetExePath()
        => Path.Combine(AppContext.BaseDirectory, AppExe);
}
```

---

## 14. Configuration appsettings.json

```json
{
  "ConnectionStrings": {
    "DefaultConnection": "Server=localhost;Database=FinAnnee;Trusted_Connection=True;TrustServerCertificate=True;"
  },
  "FinAnnee": {
    "AppName": "FinAnnee",
    "Culture": "fr-FR",
    "Theme": {
      "DefaultSkin": "Material",
      "DefaultPalette": "Light",
      "Colors": [
        "138,212,235", "245,130,49",  "60,180,75",   "230,25,75",
        "255,225,25",  "0,130,200",   "245,130,48",  "145,30,180",
        "70,240,240",  "240,50,230",  "210,245,60",  "250,190,212",
        "0,128,128",   "220,190,255", "170,110,40",  "255,250,200",
        "128,0,0",     "170,255,195", "128,128,0",   "255,215,180",
        "240,128,128"
      ]
    },
    "GridView": {
      "DefaultMaxColumns": 50,
      "PageSize": 20
    },
    "Dashboard": {
      "RefreshInterval": 60000,
      "DefaultDateRange": "CurrentMonth"
    },
    "Export": {
      "MaxRows": 100000,
      "TempDirectory": "Temp/Exports"
    },
    "Sage": {
      "Enabled": true,
      "AutoSync": false
    }
  },
  "CircuitOptions": {
    "DisconnectedCircuitRetentionPeriod": "00:30:00"
  },
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning"
    }
  },
  "AllowedHosts": "*"
}
```

---

## 15. Sécurité

### 15.1 Chiffrement mot de passe CompanyConnection

```csharp
// EncryptionHelper.cs — AES-256
public static class EncryptionHelper
{
    private static readonly byte[] Key = Convert.FromBase64String(
        "VOTRE_CLE_AES256_BASE64_32BYTES==");  // À stocker en secret/env var

    public static string Encrypt(string plainText)
    {
        using var aes = Aes.Create();
        aes.Key = Key;
        aes.GenerateIV();
        using var encryptor = aes.CreateEncryptor();
        using var ms  = new MemoryStream();
        ms.Write(aes.IV, 0, aes.IV.Length);
        using (var cs = new CryptoStream(ms, encryptor, CryptoStreamMode.Write))
        using (var sw = new StreamWriter(cs))
            sw.Write(plainText);
        return Convert.ToBase64String(ms.ToArray());
    }

    public static string Decrypt(string cipherText)
    {
        var bytes = Convert.FromBase64String(cipherText);
        using var aes = Aes.Create();
        aes.Key = Key;
        aes.IV  = bytes[..16];
        using var decryptor = aes.CreateDecryptor();
        using var ms = new MemoryStream(bytes[16..]);
        using var cs = new CryptoStream(ms, decryptor, CryptoStreamMode.Read);
        using var sr = new StreamReader(cs);
        return sr.ReadToEnd();
    }
}
```

### 15.2 Requêtes paramétrées (anti-injection SQL)

```csharp
// TOUJOURS utiliser des paramètres — jamais de concaténation
using var conn = new SqlConnection(connectionString);
using var cmd  = new SqlCommand(query, conn);
foreach (var (key, value) in parameters)
    cmd.Parameters.AddWithValue("@" + key, value ?? DBNull.Value);
await conn.OpenAsync();
using var reader = await cmd.ExecuteReaderAsync();
```

### 15.3 Autorisation Blazor

```razor
@attribute [Authorize]                    // Authentifié obligatoire
@attribute [Authorize(Roles = "Admin")]   // Admin seulement

@inject IAuthenticationService Auth

@if (Auth.IsSuperAdmin())
{
    <MudNavLink Href="/admin/clr">CLR SQL Server</MudNavLink>
}
```

---

## 16. Déploiement

### 16.1 Commandes de création du projet

```bash
# Créer la solution
cd D:\FinAnnee
dotnet new sln -n FinAnnee

# Projets
dotnet new classlib  -n FinAnnee.Core      -f net9.0
dotnet new classlib  -n FinAnnee.Data      -f net9.0
dotnet new blazorserver -n FinAnnee.BlazorApp
dotnet new worker    -n FinAnnee.SyncService -f net9.0

# Ajouter à la solution
dotnet sln add FinAnnee.Core/FinAnnee.Core.csproj
dotnet sln add FinAnnee.Data/FinAnnee.Data.csproj
dotnet sln add FinAnnee.BlazorApp/FinAnnee.BlazorApp.csproj
dotnet sln add FinAnnee.SyncService/FinAnnee.SyncService.csproj

# Références entre projets
dotnet add FinAnnee.Data/FinAnnee.Data.csproj reference FinAnnee.Core/FinAnnee.Core.csproj
dotnet add FinAnnee.BlazorApp/FinAnnee.BlazorApp.csproj reference FinAnnee.Data/FinAnnee.Data.csproj
dotnet add FinAnnee.BlazorApp/FinAnnee.BlazorApp.csproj reference FinAnnee.Core/FinAnnee.Core.csproj
dotnet add FinAnnee.SyncService/FinAnnee.SyncService.csproj reference FinAnnee.Core/FinAnnee.Core.csproj
dotnet add FinAnnee.SyncService/FinAnnee.SyncService.csproj reference FinAnnee.Data/FinAnnee.Data.csproj
```

### 16.2 Migration base de données

```bash
# Installer outils EF
dotnet tool install --global dotnet-ef

# Créer migration initiale
dotnet ef migrations add Initial \
  --project FinAnnee.Data \
  --startup-project FinAnnee.BlazorApp

# Appliquer
dotnet ef database update \
  --project FinAnnee.BlazorApp
```

### 16.3 Lancer l'application

```bash
dotnet run --project FinAnnee.BlazorApp
# → http://localhost:5000 / https://localhost:5001
```

### 16.4 Déploiement IIS

```bash
dotnet publish FinAnnee.BlazorApp -c Release -o ./publish
```

```xml
<!-- web.config généré automatiquement -->
<configuration>
  <system.webServer>
    <aspNetCore processPath="dotnet"
                arguments=".\FinAnnee.BlazorApp.dll"
                stdoutLogEnabled="true"
                hostingModel="inprocess" />
  </system.webServer>
</configuration>
```

---

## 17. Plan de Développement par Phases

### Phase 1 — Foundation (Semaine 1-2) CRITIQUE

```
[ ] Créer solution et 4 projets
[ ] Écrire les 5 enums (BarItemType, DataSourceType, ItemDestination, SyncQueryType, SourceType)
[ ] Écrire les 13 modèles (User, Group, CompanyConnection, BarItem, SyncQuery, ...)
[ ] Créer ApplicationDbContext avec toutes les tables
[ ] Exécuter dotnet ef migrations add Initial + database update
[ ] Écrire Repository générique + UserRepository
[ ] Configurer Program.cs (DI, Identity, MudBlazor)
[ ] Créer Login.razor + AuthenticationService
[ ] Tester connexion et authentification
```

### Phase 2 — Navigation (Semaine 2-3) IMPORTANT

```
[ ] MainLayout.razor avec MudAppBar + MudDrawer
[ ] NavMenu.razor avec BarItems dynamiques depuis DB
[ ] SelectConnection.razor (sélection connexion entreprise)
[ ] Home.razor (page d'accueil)
[ ] BarItemRepository avec filtrage par groupe/connexion
[ ] DataSourceService (exécution requêtes SQL)
[ ] Tester navigation complète Login → Connection → Menu
```

### Phase 3 — GridView (Semaine 3-4)

```
[ ] GridViewComponent.razor avec MudDataGrid
[ ] Chargement DataSource depuis BarItem.DataSource (XML)
[ ] Filtrage colonnes via RightColumnItemGroup
[ ] Export Excel (EPPlus) + PDF (QuestPDF)
[ ] Sauvegarde layout dans Setting table
[ ] SparkLineColumn.razor (ApexChart inline)
```

### Phase 4 — PivotGrid (Semaine 4-5)

```
[ ] PivotService.cs (agrégation manuelle)
[ ] PivotGridComponent.razor avec drag & drop champs
[ ] PivotFieldList + PivotFieldArea
[ ] Champs calculés (ExpressionEvaluator.cs)
[ ] Top N filtering
[ ] PivotChartView (ApexChart)
[ ] Export Excel avec PivotTable native (EPPlus)
```

### Phase 5 — Dashboard (Semaine 5-6)

```
[ ] DashboardComponent.razor
[ ] DashboardCard.razor (cartes KPI)
[ ] DashboardChart.razor (ApexCharts intégrés)
[ ] DashboardFilter.razor (date range)
[ ] Refresh automatique
[ ] Configuration couleurs depuis appsettings
```

### Phase 6 — Management (Semaine 6-8)

```
[ ] BarItemManager.razor (CRUD TreeView)
[ ] UserManager + GroupManager + RightsManager
[ ] ConnectionManager + ConnectionTest
[ ] SyncQueryManager + SyncScheduler
[ ] QueryBuilder.razor
[ ] MappingEditor.razor
```

### Phase 7 — Excel & Report (Semaine 8-9)

```
[ ] ExcelComponent.razor (multi-feuilles)
[ ] ReportComponent.razor (QuestPDF)
[ ] ReportViewer.razor (aperçu PDF)
[ ] Templates header/footer avec logo
```

### Phase 8 — Sage & Avancé (Semaine 9-10)

```
[ ] HelperRegistry.cs (intégration registre Sage)
[ ] SyncService Windows Worker
[ ] Notifications temps réel (SignalR/Blazored.Toast)
[ ] Thèmes personnalisés par utilisateur
[ ] Tests et optimisations
```

---

## 18. Checklist Complète des Fichiers

### FinAnnee.Core (17 fichiers)

```
Enums/
  [ ] BarItemType.cs
  [ ] DataSourceType.cs
  [ ] ItemDestination.cs
  [ ] SyncQueryType.cs
  [ ] SourceType.cs

Models/
  [ ] User.cs
  [ ] Group.cs
  [ ] CompanyConnection.cs
  [ ] BarItem.cs
  [ ] SyncQuery.cs
  [ ] SyncQueryConnection.cs
  [ ] SyncQueryConnectionAppointment.cs
  [ ] SyncHistory.cs
  [ ] RightItemGroup.cs
  [ ] RightColumnItemGroup.cs
  [ ] RightConnectionUser.cs
  [ ] Mapping.cs
  [ ] Setting.cs
```

### FinAnnee.Data (12 fichiers)

```
  [ ] ApplicationDbContext.cs
  [ ] DynamicDbContext.cs
  Repositories/
    [ ] IRepository.cs
    [ ] Repository.cs
    [ ] IUserRepository.cs
    [ ] UserRepository.cs
    [ ] IBarItemRepository.cs
    [ ] BarItemRepository.cs
    [ ] ICompanyConnectionRepository.cs
    [ ] CompanyConnectionRepository.cs
    [ ] ISyncQueryRepository.cs
    [ ] SyncQueryRepository.cs
```

### FinAnnee.BlazorApp (~85 fichiers)

```
  [ ] Program.cs
  [ ] App.razor
  [ ] _Imports.razor
  [ ] appsettings.json
  [ ] appsettings.Development.json

  Components/Layout/
    [ ] MainLayout.razor
    [ ] MainLayout.razor.cs
    [ ] NavMenu.razor
    [ ] AppBar.razor

  Components/Pages/
    [ ] Home.razor
    [ ] Login.razor
    [ ] SelectConnection.razor
    [ ] Error.razor

  Components/Core/GridView/
    [ ] GridViewComponent.razor
    [ ] GridViewSettings.razor
    [ ] GridViewExport.razor
    [ ] SparkLineColumn.razor
    [ ] UnboundColumn.razor
    [ ] FormatColumn.razor

  Components/Core/PivotGrid/
    [ ] PivotGridComponent.razor
    [ ] PivotFieldList.razor
    [ ] PivotFieldArea.razor
    [ ] PivotFieldSettings.razor
    [ ] PivotCalculatedField.razor
    [ ] PivotTopNFilter.razor
    [ ] PivotChartView.razor
    [ ] PivotDrillDown.razor

  Components/Core/Dashboard/
    [ ] DashboardComponent.razor
    [ ] DashboardCard.razor
    [ ] DashboardChart.razor
    [ ] DashboardFilter.razor
    [ ] DashboardSettings.razor

  Components/Core/Excel/
    [ ] ExcelComponent.razor
    [ ] ExcelWorksheet.razor
    [ ] ExcelExport.razor

  Components/Core/Report/
    [ ] ReportComponent.razor
    [ ] ReportViewer.razor
    [ ] ReportSettings.razor

  Components/Management/BarItem/
    [ ] BarItemManager.razor
    [ ] BarItemForm.razor
    [ ] DataSourceEditor.razor
    [ ] QueryBuilder.razor
    [ ] QueryParameter.razor
    [ ] MappingEditor.razor
    [ ] IconSelector.razor

  Components/Management/User/
    [ ] UserManager.razor
    [ ] UserForm.razor
    [ ] GroupManager.razor
    [ ] GroupForm.razor
    [ ] RightsManager.razor
    [ ] ThemeSelector.razor

  Components/Management/SyncQuery/
    [ ] SyncQueryManager.razor
    [ ] SyncQueryForm.razor
    [ ] SyncScheduler.razor
    [ ] SyncServiceControl.razor
    [ ] SyncHistory.razor

  Components/Management/Connection/
    [ ] ConnectionManager.razor
    [ ] ConnectionForm.razor
    [ ] ConnectionTest.razor

  Services/
    [ ] IAuthenticationService.cs
    [ ] AuthenticationService.cs
    [ ] IDataSourceService.cs
    [ ] DataSourceService.cs
    [ ] IExportService.cs
    [ ] ExportService.cs
    [ ] IPivotService.cs
    [ ] PivotService.cs
    [ ] ILayoutService.cs
    [ ] LayoutService.cs
    [ ] IThemeService.cs
    [ ] ThemeService.cs

  Helpers/
    [ ] QueryHelper.cs
    [ ] MappingHelper.cs
    [ ] ExpressionEvaluator.cs
    [ ] DataTableHelper.cs
    [ ] EncryptionHelper.cs
    [ ] HelperRegistry.cs    ← Intégration Sage registre

  wwwroot/
    [ ] css/app.css
    [ ] css/mudblazor-custom.css
    [ ] js/interop.js
    [ ] js/apexcharts-interop.js
    [ ] favicon.ico
```

### FinAnnee.SyncService (4 fichiers)

```
  [ ] Program.cs
  [ ] SyncWorker.cs
  [ ] SyncExecutor.cs
  [ ] appsettings.json
```

---

## Ressources

| Technologie | Documentation |
|------------|---------------|
| ASP.NET Core 9 Blazor | https://learn.microsoft.com/aspnet/core/blazor |
| MudBlazor 8.x | https://mudblazor.com/docs/overview |
| ApexCharts Blazor | https://apexcharts.github.io/Blazor-ApexCharts |
| QuestPDF | https://www.questpdf.com/documentation |
| EPPlus | https://github.com/EPPlusSoftware/EPPlus/wiki |
| Entity Framework Core 9 | https://learn.microsoft.com/ef/core |
| ASP.NET Core Identity | https://learn.microsoft.com/aspnet/core/security/authentication/identity |

---

**Total estimé : ~120 fichiers | ~18 500 lignes de code**
**Source de référence : `D:\new projects\OptiBoard`**
**Auteur du guide : Claude (Anthropic) — 2026-03-27**
