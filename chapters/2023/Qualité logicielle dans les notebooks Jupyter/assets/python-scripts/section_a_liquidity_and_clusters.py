#!/usr/bin/env python
# coding: utf-8

# # Liquidity through the QES-Marquee prism
# - Liquidity refers to the ease of trading a particular asset, usually defined by the avoidance of market impact while trading
# - There are several ways of understanding liquidity, the most natural looking at the amount of volume that can be accessed while trading
# - Better prediction of the amount of volume available for trading, helps avoid opportunity cost as well as excessive market impact
# - One can analyse stocks by also exploring our market impact estimates as well as our trade clusters, that try to characterise stocks with similar microstructure dynamics
# 
# <img src= "images/liquidity_forecast_img1.png"  width="800">
# Source: GS Global Markets Division 2021 

# #### Import Libraries and Utilities

# In[ ]:


from gs_quant.markets.securities import SecurityMaster, AssetIdentifier, AssetType
from gs_quant.session import GsSession, Environment
from gs_quant.data import Dataset

import datetime
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import copy
import seaborn as sns
plt.rcParams['figure.figsize'] = (16,16 / 1.62)
plt.rcParams.update({'font.size': 20})

# #### Supply Credentials

# In[ ]:


# external users should substitute their client id and secret; please skip this step if using internal jupyterhub
GsSession.use(Environment.PROD, client_id=client_id, client_secret=client_secret, scopes=('read_product_data',))

# In[ ]:


date = datetime.date(2021, 6, 9)
palette = ['#939393', '#7399c6', '#314c74','#434343']

# ## Understanding the liquidity of the market

# ### How can I get the market-wide Volume Profiles for an index (e.g. FTSE 100, CAC 40, DAX 30, ATX 20) built from its constituents?

# In[ ]:


def grabIndexData(index, dateDT, datasetId):
    ind = SecurityMaster.get_asset(index, AssetIdentifier.BLOOMBERG_ID, asset_type=AssetType.INDEX)
    tradedStocks  = list(filter(None, ind.get_entity()['underlying_asset_ids'])) 
    dt = Dataset(datasetId).get_data(dateDT, dateDT, assetId=tradedStocks, limit=50000)
    dt['index'] = index
    return dt

# In[ ]:


indicesEuro = ['UKX', 'DAX', 'CAC', 'ATX']
dataId = 'SINGLE_STOCK_VOLUME_PROFILE_BASE'
fields = ['cumulativeVolumeInPercentage', 'bucketStartTime', 'assetId']
volumeProfileIndexEuro = pd.concat([grabIndexData(index, date, dataId)[fields] for index in indicesEuro], axis=0)
volumeProfileIndexEuro.head()

# In[ ]:


volumeProfileIndexEuroMean = volumeProfileIndexEuro.loc[str(date)].groupby(by=['index', 'bucketStartTime']).mean()
volumeProfileIndexEuroMean['index'] = volumeProfileIndexEuroMean.index.get_level_values(0)
volumeProfileIndexEuroMean['bucketStartTime'] = volumeProfileIndexEuroMean.index.get_level_values(1).time.astype('str')

plt.figure(figsize=(15, 10))
figs = sns.lineplot(x='bucketStartTime', y='cumulativeVolumeInPercentage', hue='index', palette=palette,
                    data=volumeProfileIndexEuroMean)
for ind, label in enumerate(figs.get_xticklabels()):
    label.set_visible(True if ind % 10 == 0 else False)

xlabel = plt.xlabel('bucketStartTime (GMT Time)', fontsize = 18)
x = plt.xticks(size=18, rotation=90)
y = plt.yticks(size=18)
figs.xaxis.set_label_coords(0.5, -0.2)
title = plt.title('Average Start of Day Volume Profiles for Select Indices (09/06/2021)', fontsize=20)

# ### Intraday, do I get a real-time updated forecast? Does it make any difference?

# <img src= "images/liquidity_forecast_img3.png">
# Source: GS Global Markets Division, Reuters, 01Jan19-31Dec19
# 

# ### How is it constructed?

# <img src= "images/liquidity_forecast_method_img1.png">
# Source: GS Global Markets Division 2021

# In[ ]:


indicesEuro = ['UKX', 'DAX', 'CAC', 'ATX']
dataId = 'SINGLE_STOCK_VOLUME_FORECAST_BASE'
dateTime=datetime.datetime(2021, 6, 9, 11, 0, 0)
volumeUpdateIndexEuro = pd.concat([grabIndexData(index, dateTime, dataId) for index in indicesEuro], axis=0)
volumeUpdateIndexEuro.head()

# In[ ]:


volumeUpdateIndexEuro.groupby('index')['volumeForecastAdjustment'].describe()[['mean', 'std', 'min', '25%', '50%', '75%']]

# ## What if I am interested in a single stock?

# In[ ]:


ds = Dataset('SINGLE_STOCK_VOLUME_FORECAST_BASE')
volumeUpdateAsset = ds.get_data(dateTime, dateTime, bbid='VOD LN', limit=5000)
volumeUpdateAsset

# In[ ]:


dsp = Dataset('SINGLE_STOCK_VOLUME_PROFILE_BASE')
volumeProfileAsset= dsp.get_data(date, date, bbid='VOD LN', limit=5000)

# In[ ]:


volumeProfileStatic = volumeProfileAsset[['cumulativeVolumeInShares', 'bucketVolumeInShares', 'bucketStartTime', 'bbid']].loc[str(date_].groupby(by=['bbid', 'bucketStartTime']).mean()
volumeProfileStatic['VolumeInSharesUpdated'] = volumeProfileStatic['bucketVolumeInShares']*volumeUpdateAsset['volumeForecastAdjustment'][0]
volumeProfileForecast = volumeProfileStatic[ volumeProfileStatic.index.get_level_values(1).time>=datetime.time(11, 0, 0)]
volumeProfileForecast = volumeProfileForecast[['bucketVolumeInShares', 'VolumeInSharesUpdated']].cumsum().reset_index()
volumeProfileForecast['bucketStartTime'] = volumeProfileForecast['bucketStartTime'].dt.time.astype('str')
plt.figure(figsize=(15, 10))

figs = sns.lineplot(x='bucketStartTime', y='bucketVolumeInShares', data=volumeProfileForecast,label='Static Prediction', color=palette[1])
figs = sns.lineplot(x='bucketStartTime', y='VolumeInSharesUpdated', data=volumeProfileForecast,label='Dynamic Prediction', color=palette[2])
figs.lines[1].set_linestyle('--')

for ind, label in enumerate(figs.get_xticklabels()):
    label.set_visible(True if ind % 10 == 0 else False)
xlabel = plt.xlabel('bucketStartTime (GMT Time)')
plt.legend()

x = plt.xticks(size=18, rotation=90)
y = plt.yticks(size=18)
coords = figs.xaxis.set_label_coords(0.5, -0.2)
title = plt.title('Static and Dynamic Volume Profile Prediction (VOD LN 09/06/2021)', fontsize = 20)

# ## Market Impact and Microstructure Stock clusters

# <img src= "images/clusteringImg.png">
# Source: GS Global Markets Division 2021

# ### Query Market Impact Estimates for STOXX Total Market Index

# In[ ]:


def fn_marketImpactEstimates(index, date):
    #List of stocks traded in a particular index
    ind = SecurityMaster.get_asset(index, AssetIdentifier.BLOOMBERG_ID, asset_type=AssetType.INDEX)
    tradedStocks = list(filter(None, ind.get_entity()['underlying_asset_ids']))
    ds = Dataset('SINGLE_STOCK_MARKET_IMPACT')
    return ds.get_data(date, date, assetId=tradedStocks, percentADV=[1,5,10], limit=50000)

marketImpactEstimates = fn_marketImpactEstimates('BKXP', date)

# ### Query Trade Clusters for STOXX Total Market Index

# In[ ]:


df_clusters = grabIndexData('BKXP', date, 'EQTRADECLUSTERS')
df_clusters

# In[ ]:


data_01pov = marketImpactEstimates[(marketImpactEstimates['percentADV']==1) & (marketImpactEstimates['participationRate']==1)]
data_05pov = marketImpactEstimates[(marketImpactEstimates['percentADV']==5) & (marketImpactEstimates['participationRate']==5)]
data_10pov = marketImpactEstimates[(marketImpactEstimates['percentADV']==10) & (marketImpactEstimates['participationRate']==10)]
data_marketImpact = pd.concat([data_01pov, data_05pov, data_10pov])
data_marketImpact_clusters = pd.merge(data_marketImpact, df_clusters[['assetId', 'clusterClass']], how='left', on=['assetId'])
data_marketImpact_clusters['clusterClass'] = data_marketImpact_clusters['clusterClass'].astype('int')
data_marketImpact_clusters.sort_values('clusterClass', inplace=True)
data_marketImpact_clusters

# In[ ]:


bp = sns.boxplot(y='estimatedImpact', x='clusterClass', data=data_marketImpact_clusters,
                 palette=palette, hue='percentADV')

handles, labels = bp.get_legend_handles_labels()
plt.xticks(fontsize=15)
plt.yticks(fontsize=15)
figs = plt.legend(handles[0:3], ['1%', '5%' , '10%'], title='POV', fontsize=15, title_fontsize=18)
plt.title('Estimated Impact by Cluster for different POV rates', fontsize=20)
l = plt.ylim([0, 40])

# ##### Disclaimers:
# ###### Indicative Terms/Pricing Levels: This material may contain indicative terms only, including but not limited to pricing levels. There is no representation that any transaction can or could have been effected at such terms or prices. Proposed terms and conditions are for discussion purposes only. Finalized terms and conditions are subject to further discussion and negotiation.
# ###### www.goldmansachs.com/disclaimer/sales-and-trading-invest-rec-disclosures.html If you are not accessing this material via Marquee ContentStream, a list of the author's investment recommendations disseminated during the preceding 12 months and the proportion of the author's recommendations that are 'buy', 'hold', 'sell' or other over the previous 12 months is available by logging into Marquee ContentStream using the link below. Alternatively, if you do not have access to Marquee ContentStream, please contact your usual GS representative who will be able to provide this information to you.
# ###### Please refer to https://marquee.gs.com/studio/ for price information of corporate equity securities.
# ###### Notice to Australian Investors: When this document is disseminated in Australia by Goldman Sachs & Co. LLC ("GSCO"), Goldman Sachs International ("GSI"), Goldman Sachs Bank Europe SE ("GSBE"), Goldman Sachs (Asia) L.L.C. ("GSALLC"), or Goldman Sachs (Singapore) Pte ("GSSP") (collectively the "GS entities"), this document, and any access to it, is intended only for a person that has first satisfied the GS entities that: 
# ###### • the person is a Sophisticated or Professional Investor for the purposes of section 708 of the Corporations Act of Australia; and 
# ###### • the person is a wholesale client for the purpose of section 761G of the Corporations Act of Australia. 
# ###### To the extent that the GS entities are providing a financial service in Australia, the GS entities are each exempt from the requirement to hold an Australian financial services licence for the financial services they provide in Australia. Each of the GS entities are regulated by a foreign regulator under foreign laws which differ from Australian laws, specifically: 
# ###### • GSCO is regulated by the US Securities and Exchange Commission under US laws;
# ###### • GSI is authorised by the Prudential Regulation Authority and regulated by the Financial Conduct Authority and the Prudential Regulation Authority, under UK laws;
# ###### • GSBE is subject to direct prudential supervision by the European Central Bank and in other respects is supervised by the German Federal Financial Supervisory Authority (Bundesanstalt für Finanzdienstleistungsaufischt, BaFin) and Deutsche Bundesbank;
# ###### • GSALLC is regulated by the Hong Kong Securities and Futures Commission under Hong Kong laws; and
# ###### • GSSP is regulated by the Monetary Authority of Singapore under Singapore laws.
# ###### Notice to Brazilian Investors
# ###### Marquee is not meant for the general public in Brazil. The services or products provided by or through Marquee, at any time, may not be offered or sold to the general public in Brazil. You have received a password granting access to Marquee exclusively due to your existing relationship with a GS business located in Brazil. The selection and engagement with any of the offered services or products through Marquee, at any time, will be carried out directly by you. Before acting to implement any chosen service or products, provided by or through Marquee you should consider, at your sole discretion, whether it is suitable for your particular circumstances and, if necessary, seek professional advice. Any steps necessary in order to implement the chosen service or product, including but not limited to remittance of funds, shall be carried out at your discretion. Accordingly, such services and products have not been and will not be publicly issued, placed, distributed, offered or negotiated in the Brazilian capital markets and, as a result, they have not been and will not be registered with the Brazilian Securities and Exchange Commission (Comissão de Valores Mobiliários), nor have they been submitted to the foregoing agency for approval. Documents relating to such services or products, as well as the information contained therein, may not be supplied to the general public in Brazil, as the offering of such services or products is not a public offering in Brazil, nor used in connection with any offer for subscription or sale of securities to the general public in Brazil.
# ###### The offer of any securities mentioned in this message may not be made to the general public in Brazil. Accordingly, any such securities have not been nor will they be registered with the Brazilian Securities and Exchange Commission (Comissão de Valores Mobiliários) nor has any offer been submitted to the foregoing agency for approval. Documents relating to the offer, as well as the information contained therein, may not be supplied to the public in Brazil, as the offer is not a public offering of securities in Brazil. These terms will apply on every access to Marquee.
# ###### Ouvidoria Goldman Sachs Brasil: 0800 727 5764 e/ou ouvidoriagoldmansachs@gs.com
# ###### Horário de funcionamento: segunda-feira à sexta-feira (exceto feriados), das 9hs às 18hs.
# ###### Ombudsman Goldman Sachs Brazil: 0800 727 5764 and / or ouvidoriagoldmansachs@gs.com
# ###### Available Weekdays (except holidays), from 9 am to 6 pm.
#  
# ###### Note to Investors in Israel: GS is not licensed to provide investment advice or investment management services under Israeli law.
# ###### Notice to Investors in Japan
# ###### Marquee is made available in Japan by Goldman Sachs Japan Co., Ltd.
# 
# ###### 本書は情報の提供を目的としております。また、売却・購入が違法となるような法域での有価証券その他の売却若しくは購入を勧めるものでもありません。ゴールドマン・サックスは本書内の取引又はストラクチャーの勧誘を行うものではございません。これらの取引又はストラクチャーは、社内及び法規制等の承認等次第で実際にはご提供できない場合がございます。
# 
# ###### <適格機関投資家限定　転売制限>
# ###### ゴールドマン・サックス証券株式会社が適格機関投資家のみを相手方として取得申込みの勧誘（取得勧誘）又は売付けの申込み若しくは買付けの申込みの勧誘(売付け勧誘等)を行う本有価証券には、適格機関投資家に譲渡する場合以外の譲渡が禁止される旨の制限が付されています。本有価証券は金融商品取引法第４条に基づく財務局に対する届出が行われておりません。なお、本告知はお客様によるご同意のもとに、電磁的に交付させていただいております。
# ###### ＜適格機関投資家用資料＞ 
# ###### 本資料は、適格機関投資家のお客さまのみを対象に作成されたものです。本資料における金融商品は適格機関投資家のお客さまのみがお取引可能であり、適格機関投資家以外のお客さまからのご注文等はお受けできませんので、ご注意ください。 商号等/ゴールドマン・サックス証券株式会社 金融商品取引業者　関東財務局長（金商）第６９号 
# ###### 加入協会/　日本証券業協会、一般社団法人金融先物取引業協会、一般社団法人第二種金融商品取引業協会 
# ###### 本書又はその添付資料に信用格付が記載されている場合、日本格付研究所（JCR）及び格付投資情報センター（R&I）による格付は、登録信用格付業者による格付（登録格付）です。その他の格付は登録格付である旨の記載がない場合は、無登録格付です。無登録格付を投資判断に利用する前に、「無登録格付に関する説明書」（http://www.goldmansachs.com/disclaimer/ratings.html）を十分にお読みください。 
# ###### If any credit ratings are contained in this material or any attachments, those that have been issued by Japan Credit Rating Agency, Ltd. (JCR) or Rating and Investment Information, Inc. (R&I) are credit ratings that have been issued by a credit rating agency registered in Japan (registered credit ratings). Other credit ratings are unregistered unless denoted as being registered. Before using unregistered credit ratings to make investment decisions, please carefully read "Explanation Regarding Unregistered Credit Ratings" (http://www.goldmansachs.com/disclaimer/ratings.html).
# ###### Notice to Mexican Investors: Information contained herein is not meant for the general public in Mexico. The services or products provided by or through Goldman Sachs Mexico, Casa de Bolsa, S.A. de C.V. (GS Mexico) may not be offered or sold to the general public in Mexico. You have received information herein exclusively due to your existing relationship with a GS Mexico or any other Goldman Sachs business. The selection and engagement with any of the offered services or products through GS Mexico will be carried out directly by you at your own risk. Before acting to implement any chosen service or product provided by or through GS Mexico you should consider, at your sole discretion, whether it is suitable for your particular circumstances and, if necessary, seek professional advice. Information contained herein related to GS Mexico services or products, as well as any other information, shall not be considered as a product coming from research, nor it contains any recommendation to invest, not to invest, hold or sell any security and may not be supplied to the general public in Mexico.
# ###### Notice to New Zealand Investors: When this document is disseminated in New Zealand by Goldman Sachs & Co. LLC ("GSCO") , Goldman Sachs International ("GSI"), Goldman Sachs Bank Europe SE ("GSBE"), Goldman Sachs (Asia) L.L.C. ("GSALLC") or Goldman Sachs (Singapore) Pte ("GSSP") (collectively the "GS entities"), this document, and any access to it, is intended only for a person that has first satisfied; the GS entities that the person is someone: 
# ###### (i) who is an investment business within the meaning of clause 37 of Schedule 1 of the Financial Markets Conduct Act 2013 (New Zealand) (the "FMC Act");
# ###### (ii) who meets the investment activity criteria specified in clause 38 of Schedule 1 of the FMC Act;
# ###### (iii) who is large within the meaning of clause 39 of Schedule 1 of the FMC Act; or
# ###### (iv) is a government agency within the meaning of clause 40 of Schedule 1 of the FMC Act. 
# ###### No offer to acquire the interests is being made to you in this document. Any offer will only be made in circumstances where disclosure is not required under the Financial Markets Conducts Act 2013 or the Financial Markets Conduct Regulations 2014.
# ###### Notice to Swiss Investors: This is marketing material for financial instruments or services. The information contained in this material is for general informational purposes only and does not constitute an offer, solicitation, invitation or recommendation to buy or sell any financial instruments or to provide any investment advice or service of any kind.
# ###### THE INFORMATION CONTAINED IN THIS DOCUMENT DOES NOT CONSITUTE, AND IS NOT INTENDED TO CONSTITUTE, A PUBLIC OFFER OF SECURITIES IN THE UNITED ARAB EMIRATES IN ACCORDANCE WITH THE COMMERCIAL COMPANIES LAW (FEDERAL LAW NO. 2 OF 2015), ESCA BOARD OF DIRECTORS' DECISION NO. (9/R.M.) OF 2016, ESCA CHAIRMAN DECISION NO 3/R.M. OF 2017 CONCERNING PROMOTING AND INTRODUCING REGULATIONS OR OTHERWISE UNDER THE LAWS OF THE UNITED ARAB EMIRATES. ACCORDINGLY, THE INTERESTS IN THE SECURITIES MAY NOT BE OFFERED TO THE PUBLIC IN THE UAE (INCLUDING THE DUBAI INTERNATIONAL FINANCIAL CENTRE AND THE ABU DHABI GLOBAL MARKET). THIS DOCUMENT HAS NOT BEEN APPROVED BY, OR FILED WITH THE CENTRAL BANK OF THE UNITED ARAB EMIRATES, THE SECURITIES AND COMMODITIES AUTHORITY, THE DUBAI FINANCIAL SERVICES AUTHORITY, THE FINANCIAL SERVICES REGULATORY AUTHORITY OR ANY OTHER RELEVANT LICENSING AUTHORITIES IN THE UNITED ARAB EMIRATES. IF YOU DO NOT UNDERSTAND THE CONTENTS OF THIS DOCUMENT, YOU SHOULD CONSULT WITH A FINANCIAL ADVISOR. THIS DOCUMENT IS PROVIDED TO THE RECIPIENT ONLY AND SHOULD NOT BE PROVIDED TO OR RELIED ON BY ANY OTHER PERSON.
